"""
ทดสอบระบบบัญชีผู้ใช้ ทั้งการทำงานและข้อกำหนดด้านความเป็นส่วนตัว
"""
from app.db.database import SessionLocal
from app.db.models import AppUser, UserSession

EMAIL = "Somchai.Test@Example.com"
PASSWORD = "correct-horse-42"


def _register(client, email=EMAIL, password=PASSWORD, consent=True):
    return client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "accept_privacy_policy": consent},
    )


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


def test_register_logs_in_and_returns_profile(client):
    resp = _register(client)
    assert resp.status_code == 201
    body = resp.json()
    assert body["token"]
    assert body["user"]["email"] == "somchai.test@example.com"   # เก็บเป็นตัวพิมพ์เล็ก
    assert body["user"]["consent_version"]

    me = client.get("/api/v1/auth/me", headers=_auth(body["token"]))
    assert me.status_code == 200
    assert me.json()["email"] == "somchai.test@example.com"
    # เวลาต้องมี timezone กำกับ ไม่งั้นเบราว์เซอร์แสดงผิดเป็นเวลาท้องถิ่น
    assert me.json()["created_at"].endswith(("Z", "+00:00"))


def test_register_requires_consent_valid_email_and_long_password(client):
    assert _register(client, consent=False).status_code == 422
    assert _register(client, email="not-an-email").status_code == 422
    assert _register(client, password="short").status_code == 422


def test_register_rejects_duplicate_email_case_insensitive(client):
    assert _register(client).status_code == 201
    assert _register(client, email=EMAIL.upper()).status_code == 409


def test_database_has_no_plaintext_email_password_or_token(client):
    token = _register(client).json()["token"]
    with SessionLocal() as db:
        user = db.query(AppUser).one()
        session = db.query(UserSession).one()
        stored = " ".join([user.email_hash, user.email_encrypted, user.password_hash, session.token_hash])
    assert "somchai" not in stored.lower()
    assert PASSWORD not in stored
    assert token not in stored
    assert user.password_hash.startswith("scrypt$")


def test_login_error_is_identical_for_unknown_email_and_wrong_password(client):
    _register(client)
    wrong_password = client.post("/api/v1/auth/login", json={"email": EMAIL, "password": "wrong-password"})
    unknown_email = client.post("/api/v1/auth/login", json={"email": "nobody@example.com", "password": PASSWORD})
    assert wrong_password.status_code == unknown_email.status_code == 401
    assert wrong_password.json() == unknown_email.json()


def test_login_then_logout_revokes_token_on_server(client):
    _register(client)
    resp = client.post("/api/v1/auth/login", json={"email": EMAIL, "password": PASSWORD})
    assert resp.status_code == 200
    token = resp.json()["token"]

    assert client.post("/api/v1/auth/logout", headers=_auth(token)).status_code == 204
    assert client.get("/api/v1/auth/me", headers=_auth(token)).status_code == 401


def test_delete_account_needs_password_and_removes_every_row(client):
    token = _register(client).json()["token"]
    wrong = client.request("DELETE", "/api/v1/auth/me", headers=_auth(token), json={"password": "wrong-password"})
    assert wrong.status_code == 403

    ok = client.request("DELETE", "/api/v1/auth/me", headers=_auth(token), json={"password": PASSWORD})
    assert ok.status_code == 204
    with SessionLocal() as db:
        assert db.query(AppUser).count() == 0
        assert db.query(UserSession).count() == 0
    assert client.post("/api/v1/auth/login", json={"email": EMAIL, "password": PASSWORD}).status_code == 401


def test_login_is_rate_limited(client):
    from app.api.rate_limit import auth_limiter

    codes = [
        client.post("/api/v1/auth/login", json={"email": EMAIL, "password": "guess"}).status_code
        for _ in range(auth_limiter.limit + 1)
    ]
    assert codes[-1] == 429
    assert set(codes[:-1]) == {401}


def test_analyze_still_works_without_login(client):
    resp = client.post("/api/v1/analyze", json={"subject": "Meeting", "body_content": "See you on Friday."})
    assert resp.status_code == 200
