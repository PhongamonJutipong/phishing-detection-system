"""
ทดสอบ API ตาม UC-04 / UC-05 / UC-06 ด้วยโมเดลขนาดเล็กของจริง (ดู conftest.py)
"""
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
    resp = client.get("/")
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]
    assert "analyze-form" in resp.text
    assert client.get("/app.js").status_code == 200
    assert client.get("/style.css").status_code == 200


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


def test_scan_is_saved_per_erd_and_content_is_not_duplicated(client):
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


def test_admin_endpoints_require_token(client):
    assert client.get("/api/v1/stats").status_code == 401
    resp = client.get("/api/v1/stats", headers={"X-Admin-Token": "test-admin-token"})
    assert resp.status_code == 200
    assert "total_scans" in resp.json()
    reload = client.post("/api/v1/model/reload", headers={"X-Admin-Token": "test-admin-token"})
    assert reload.status_code == 200
