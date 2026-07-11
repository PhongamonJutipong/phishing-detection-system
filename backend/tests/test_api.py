"""
Smoke test ของ FastAPI endpoints — ไม่พึ่งไฟล์โมเดล .pkl จริง (ใช้ FakeModelService
override ผ่าน dependency_overrides แทน) เพื่อให้ test รันผ่านได้แม้ยังไม่ได้เทรนโมเดล
หรือรันบนเครื่อง CI ที่ไม่มีไฟล์ ml_model/*.pkl
"""
from fastapi.testclient import TestClient


class FakeModelService:
    metadata = {"model_type": "fake-for-test", "metrics": {"accuracy": 0.99}}

    def predict(self, subject: str, body: str) -> dict:
        is_phishing = "urgent" in body.lower() or "verify" in body.lower()
        return {
            "risk_score": 0.95 if is_phishing else 0.05,
            "is_phishing": is_phishing,
            "highlights": [{"phrase": "urgent", "reason": "ความเร่งด่วน"}] if is_phishing else [],
        }


def _make_client():
    from app.main import app
    from app.ml.model_service import get_model_service

    app.dependency_overrides[get_model_service] = lambda: FakeModelService()
    return TestClient(app)


def test_root_returns_ok():
    client = _make_client()
    resp = client.get("/")
    assert resp.status_code == 200
    assert "message" in resp.json()


def test_health_check():
    client = _make_client()
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_model_info_reflects_injected_fake_model():
    client = _make_client()
    resp = client.get("/api/v1/model-info")
    assert resp.status_code == 200
    body = resp.json()
    assert body["available"] is True
    assert body["model_type"] == "fake-for-test"


def test_analyze_flags_phishing_email():
    client = _make_client()
    resp = client.post(
        "/api/v1/analyze",
        json={"subject": "Urgent!", "body": "Please verify your account urgent now"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_phishing"] is True
    assert 0.0 <= data["risk_score"] <= 1.0
    assert len(data["highlights"]) >= 1


def test_analyze_caches_repeat_email_by_hash():
    client = _make_client()
    payload = {"subject": "Hi", "body": "just checking in about the meeting"}
    first = client.post("/api/v1/analyze", json=payload)
    second = client.post("/api/v1/analyze", json=payload)
    assert first.status_code == second.status_code == 200
    # ครั้งที่สองต้องคืนผลเดิมจาก cache (content_hash เดียวกัน) ไม่ใช่ error
    assert first.json()["risk_score"] == second.json()["risk_score"]
