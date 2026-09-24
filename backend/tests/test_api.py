"""
ทดสอบ API ตาม UC-04 / UC-05 / UC-06 ด้วยโมเดลขนาดเล็กของจริง (ดู conftest.py)
"""
import pytest

from app.config import settings
from app.db.database import SessionLocal
from app.db.database_manager import DatabaseManager
from app.db.models import DetectionModel, DetectionResult, Email, FeatureVector, TfidfFeature, TokenizedWord

EN_PHISHING = {
    "subject": "Security alert",
    "body_content": "Urgent: your account has been suspended. Please verify your identity immediately "
                    "and confirm your password at http://secure-update-login.com within 24 hours.",
}
EN_NORMAL = {"subject": "Meeting", "body_content": "Hi team, attaching the minutes from today's meeting. See you on Friday."}
TH_PHISHING = {
    "subject": "[แจ้งเตือนด่วน] บัญชีของคุณถูกระงับชั่วคราว",
    "body_content": "กรุณายืนยันตัวตนและกรอกรหัสผ่านภายใน 24 ชั่วโมง มิฉะนั้นบัญชีจะถูกปิดถาวร http://verify-login.com",
}


def test_api_root_returns_ok(client):
    resp = client.get("/api")
    assert resp.status_code == 200
    assert "message" in resp.json()


def test_web_page_is_served(client):
    """หน้าเว็บสำหรับกรอกอีเมลถูกเสิร์ฟจาก origin เดียวกับ API"""
    from app.main import WEB_DIR

    if not (WEB_DIR / "index.html").is_file():
        pytest.skip("ยังไม่ได้ build หน้าเว็บ — สั่ง 'npm run build' ในโฟลเดอร์ frontend")

    landing = client.get("/")
    assert landing.status_code == 200
    assert "text/html" in landing.headers["content-type"]
    assert "<app-root>" in landing.text          # เป็นหน้า Angular จริง

    # Angular ใช้ routing แบบ path เส้นทางเหล่านี้ไม่มีไฟล์จริงบนดิสก์
    # เซิร์ฟเวอร์ต้องคืน index.html ให้ ไม่ใช่ 404 มิฉะนั้นการรีเฟรชหน้าจะพัง
    for route in ["/scan", "/dashboard", "/login"]:
        resp = client.get(route)
        assert resp.status_code == 200, f"{route} ต้องไม่เป็น 404"
        assert "<app-root>" in resp.text


def test_health_reports_models_and_database(client):
    body = client.get("/api/v1/health").json()
    assert body["status"] == "ok"
    assert body["models_loaded"] == ["en", "th"]
    assert body["database"] == "ok"


def test_model_info_lists_each_language(client):
    body = client.get("/api/v1/model-info").json()
    assert body["available"] is True
    assert set(body["models"]) == {"en", "th"}


def test_analyze_english_phishing(client):
    resp = client.post("/api/v1/analyze", json=EN_PHISHING)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["language"] == "en"
    assert data["is_phishing"] is True
    assert data["classification"] == "phishing"
    assert data["risk_level"] == "dangerous"
    assert 50 <= data["risk_percentage"] <= 100
    assert data["suspicious_keywords"], "ควรมีคำเสี่ยงจากโมเดลสำหรับไฮไลต์"
    categories = {i["category"] for i in data["indicators"]}
    assert {"urgency", "credential_request", "suspicious_link"} <= categories
    assert data["result_id"]


def test_analyze_english_normal_email_is_safe(client):
    data = client.post("/api/v1/analyze", json=EN_NORMAL).json()
    assert data["is_phishing"] is False
    assert data["risk_level"] in {"safe", "suspicious"}


def test_analyze_thai_phishing_uses_thai_model(client):
    data = client.post("/api/v1/analyze", json=TH_PHISHING).json()
    assert data["language"] == "th"
    assert "th" in data["language_scores"]
    assert data["is_phishing"] is True


def test_analyze_rejects_blank_body(client):
    resp = client.post("/api/v1/analyze", json={"subject": "x", "body_content": "   "})
    assert resp.status_code == 422


def test_analyze_returns_503_when_no_model(client, tmp_path):
    from app.main import app
    from app.ml.model_registry import ModelRegistry, get_model_registry

    empty = ModelRegistry(str(tmp_path))
    empty.load_all()
    app.dependency_overrides[get_model_registry] = lambda: empty
    resp = client.post("/api/v1/analyze", json=EN_PHISHING)
    assert resp.status_code == 503
    assert resp.json()["code"] == "MODEL_UNAVAILABLE"


def test_scan_is_saved_per_erd_and_content_is_not_duplicated(client, monkeypatch):
    """ตารางที่ 3.9-3.14 ตาม ER diagram — ตรวจในโหมดเก็บข้อมูลวิจัยที่เปิดการเก็บครบทุกตาราง"""
    monkeypatch.setattr(settings, "store_email_content", True)
    monkeypatch.setattr(settings, "store_nlp_artifacts", True)

    client.post("/api/v1/analyze", json=EN_PHISHING)
    client.post("/api/v1/analyze", json=EN_PHISHING)

    with SessionLocal() as db:
        assert db.query(Email).count() == 1                  # UC-04 ทางเลือก 7.1: ไม่บันทึกเนื้อหาซ้ำ
        assert db.query(DetectionResult).count() == 2        # แต่บันทึกประวัติการสแกนทุกครั้ง
        assert db.query(DetectionModel).count() == 1
        assert db.query(TokenizedWord).count() > 0
        assert db.query(TfidfFeature).count() > 0
        assert db.query(FeatureVector).count() > 0

        email = db.query(Email).one()
        assert "suspended" not in email.body_encrypted      # เก็บแบบเข้ารหัส
        assert "suspended" in DatabaseManager(db).decrypt(email.body_encrypted)


def test_privacy_defaults_keep_no_content_and_no_per_email_words(client):
    """
    ค่าเริ่มต้นต้องไม่เก็บเนื้อหาอีเมลและไม่เก็บคำรายอีเมล
    แต่ยังต้องบันทึกผลการตรวจเพื่อใช้ดูสถิติได้
    """
    assert client.post("/api/v1/analyze", json=EN_PHISHING).status_code == 200

    with SessionLocal() as db:
        assert db.query(DetectionResult).count() == 1
        assert db.query(Email).one().body_encrypted is None
        # คำรายอีเมลคือช่องทางที่ทำให้ประกอบเนื้อหากลับได้ ต้องไม่มีเลยโดยค่าเริ่มต้น
        assert db.query(TokenizedWord).count() == 0
        assert db.query(TfidfFeature).count() == 0
        assert db.query(FeatureVector).count() == 0


def test_body_hash_is_keyed_so_it_cannot_be_matched_by_plain_sha256(client):
    """body_hash ต้องเป็น HMAC ที่มีกุญแจ ไม่ใช่ SHA-256 ธรรมดาที่ผู้อื่นคำนวณเทียบได้"""
    import hashlib

    client.post("/api/v1/analyze", json=EN_PHISHING)
    plain = hashlib.sha256(
        f"{EN_PHISHING['subject']}||{EN_PHISHING['body_content']}".encode("utf-8")
    ).hexdigest()

    with SessionLocal() as db:
        assert db.query(Email).one().body_hash != plain


def test_retention_deadline_is_recorded_and_expired_rows_are_purged(client, monkeypatch):
    """ข้อมูลต้องมีวันหมดอายุ และ purge_expired ต้องลบแถวที่เลยกำหนดออกจริง"""
    from datetime import datetime, timedelta, timezone

    client.post("/api/v1/analyze", json=EN_PHISHING)

    with SessionLocal() as db:
        email = db.query(Email).one()
        assert email.expires_at is not None
        # ย้อนวันหมดอายุให้เป็นอดีต เพื่อจำลองข้อมูลที่เลยกำหนดเก็บแล้ว
        email.expires_at = datetime.now(timezone.utc) - timedelta(days=1)
        db.commit()

    with SessionLocal() as db:
        assert DatabaseManager(db).purge_expired()["deleted_emails"] == 1
        assert db.query(Email).count() == 0
        assert db.query(DetectionResult).count() == 0


def test_unrecognised_text_is_not_reported_as_dangerous(client):
    """
    ข้อความที่ไม่มีคำใดอยู่ในคลังคำของโมเดลเลย ต้องไม่ถูกตัดสินว่าอันตราย

    เดิม predict_proba คืนค่า prior ของคลาส (ราว 55%) ซึ่งสูงกว่าเกณฑ์อันตราย
    ทำให้ภาษาอื่น ตัวเลขล้วน และคำที่ไม่เคยเห็น ถูกเตือนว่าอันตรายทั้งหมด
    """
    # โครงงานรองรับเฉพาะภาษาไทยและอังกฤษ จึงไม่ใช้ภาษาอื่นเป็นตัวอย่างทดสอบ
    # ใช้ตัวเลขล้วนกับคำที่ไม่มีความหมายแทน ซึ่งให้ผลเดียวกันคือเวกเตอร์ว่าง
    for text in [
        "12345 67890 11111 22222 33333",        # ตัวเลขล้วน ไม่มีคำให้ตัด
        "zzzz qqqq xxxx wwww vvvv",             # อักษรละตินที่ไม่ใช่คำ
        "ฃฃฃ ฅฅฅ ฆฆฆ ฏฏฏ ฑฑฑ",                  # อักษรไทยที่ไม่ประกอบเป็นคำ
    ]:
        body = client.post("/api/v1/analyze", json={"body_content": text}).json()
        assert body["risk_level"] != "dangerous", f"{text!r} ถูกตัดสินว่าอันตราย"
        assert body["is_phishing"] is False
        # ต้องบอกผู้ใช้ด้วยว่าทำไมถึงไม่มีผล ไม่ใช่เงียบ ๆ แล้วดูเหมือนยืนยันว่าปลอดภัย
        assert any(i["category"] == "no_known_terms" for i in body["indicators"])


def test_analyze_is_rate_limited(client, monkeypatch):
    """/analyze เปิดสาธารณะ ต้องมีเพดานคำขอกันการยิงถล่ม"""
    from app.api.rate_limit import analyze_limiter

    monkeypatch.setattr(analyze_limiter, "limit", 3)
    analyze_limiter.reset()

    codes = [client.post("/api/v1/analyze", json=EN_NORMAL).status_code for _ in range(5)]
    assert codes[:3] == [200, 200, 200]
    assert codes[3:] == [429, 429]

    analyze_limiter.reset()


def test_rate_limiter_does_not_store_raw_ip(client):
    """คีย์ที่ใช้นับต้องเป็นค่าแฮช ไม่ใช่ IP ดิบ"""
    from app.api.rate_limit import analyze_limiter

    analyze_limiter.reset()
    client.post("/api/v1/analyze", json=EN_NORMAL)
    keys = list(analyze_limiter._hits)
    assert keys and all("testclient" not in k and "127.0.0.1" not in k for k in keys)
    analyze_limiter.reset()


def test_purge_endpoint_requires_admin_token(client):
    assert client.post("/api/v1/data/purge").status_code == 401
    resp = client.post("/api/v1/data/purge", headers={"X-Admin-Token": "test-admin-token"})
    assert resp.status_code == 200
    assert "deleted_emails" in resp.json()


def test_admin_endpoints_require_token(client):
    assert client.get("/api/v1/stats").status_code == 401
    resp = client.get("/api/v1/stats", headers={"X-Admin-Token": "test-admin-token"})
    assert resp.status_code == 200
    assert "total_scans" in resp.json()

    # หน้าภาพรวมใช้ข้อมูลชุดนี้ ต้องมีระดับความเสี่ยงและรายการล่าสุด แต่ไม่มีเนื้อหาหรือผู้ส่ง
    client.post("/api/v1/analyze", json=EN_PHISHING)
    stats = client.get("/api/v1/stats", headers={"X-Admin-Token": "test-admin-token"}).json()
    assert sum(stats["risk_levels"].values()) == stats["total_scans"] >= 1
    recent = stats["recent_scans"][0]
    assert set(recent) == {"scan_time", "probability", "classification", "risk_level", "language"}
    assert recent["language"] == "en"
    assert recent["scan_time"].endswith("+00:00")
    reload = client.post("/api/v1/model/reload", headers={"X-Admin-Token": "test-admin-token"})
    assert reload.status_code == 200


def test_hashed_assets_are_cached_long_and_index_is_revalidated():
    from app.main import _cache_control_for

    for name in ("main-HCUYNKYS.js", "chunk-CpsKW6_-.js", "styles-WAJP5JCC.css"):
        assert "immutable" in _cache_control_for(name)
    for name in ("index.html", "favicon.ico", "3rdpartylicenses.txt"):
        assert _cache_control_for(name) == "no-cache"


def test_web_assets_are_gzipped_but_api_is_not(client):
    from app.main import WEB_DIR

    scripts = sorted(WEB_DIR.glob("main-*.js"))
    if not scripts:
        pytest.skip("ยังไม่ได้ build หน้าเว็บ")
    asset = client.get(f"/{scripts[0].name}", headers={"Accept-Encoding": "gzip"})
    assert asset.headers.get("content-encoding") == "gzip"
    assert "immutable" in asset.headers["cache-control"]
    spa = client.get("/scan", headers={"Accept-Encoding": "gzip"})
    assert spa.headers["cache-control"] == "no-cache"
    api = client.post("/api/v1/analyze", json=EN_NORMAL, headers={"Accept-Encoding": "gzip"})
    assert "content-encoding" not in api.headers
