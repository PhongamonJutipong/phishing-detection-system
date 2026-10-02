"""
ทดสอบการเข้าสู่ระบบด้วยบัญชี Google

ไม่ยิงจริงไปที่ Google: แทนที่ตัวตรวจลายเซ็นด้วยของปลอมที่คืน claims ตามที่กำหนด
สิ่งที่ทดสอบคือตรรกะของเราเอง (ตรวจ email_verified, การผูกบัญชี, การเก็บความยินยอม)
ส่วนการตรวจลายเซ็น JWT เป็นหน้าที่ของ google-auth ไม่ใช่สิ่งที่เราต้องพิสูจน์ซ้ำ
"""
import pytest

from app.config import settings
from app.db.database import SessionLocal
from app.db.models import AppUser

CLIENT_ID = "test-client-id.apps.googleusercontent.com"
GOOGLE_EMAIL = "Somchai.Google@Example.com"
PASSWORD = "correct-horse-42"


@pytest.fixture
def google_enabled(monkeypatch):
    monkeypatch.setattr(settings, "google_client_id", CLIENT_ID)


def _fake_claims(monkeypatch, **overrides):
    """ให้ verify_oauth2_token คืน claims ที่เราคุมได้ แทนการตรวจลายเซ็นจริง"""
    claims = {"email": GOOGLE_EMAIL, "email_verified": True, "aud": CLIENT_ID, **overrides}

    def fake_verify(token, request, audience):
        assert audience == CLIENT_ID, "ต้องส่ง client_id ไปตรวจ aud ด้วย"
        return claims

    monkeypatch.setattr("google.oauth2.id_token.verify_oauth2_token", fake_verify)
    return claims


def _google(client, **body):
    return client.post("/api/v1/auth/google", json={"id_token": "any-token-the-fake-ignores", **body})


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


def _register(client, email=GOOGLE_EMAIL, password=PASSWORD):
    return client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "accept_privacy_policy": True},
    )


class TestVerifyGoogleIdToken:
    """ตัวห่อของเราเอง ไม่ใช่การตรวจลายเซ็นของ google-auth"""

    def test_disabled_when_client_id_not_set(self):
        """ค่าเริ่มต้นคือปิด ต้องไม่แตะ library และไม่ออกเน็ต"""
        from app.services.auth_service import GoogleSignInDisabledError, verify_google_id_token

        assert settings.google_client_id == ""
        with pytest.raises(GoogleSignInDisabledError):
            verify_google_id_token("whatever")

    def test_rejects_unverified_email(self, google_enabled, monkeypatch):
        """
        สำคัญ: ลายเซ็นถูกแต่ Google ยังไม่ยืนยันอีเมล ใช้เป็นหลักฐานความเป็นเจ้าของไม่ได้
        ถ้าข้อนี้พัง จะสวมรอยเข้าบัญชีของอีเมลที่ยังไม่ยืนยันได้
        """
        from app.services.auth_service import InvalidGoogleTokenError, verify_google_id_token

        _fake_claims(monkeypatch, email_verified=False)
        with pytest.raises(InvalidGoogleTokenError):
            verify_google_id_token("t")

    def test_rejects_missing_or_malformed_email(self, google_enabled, monkeypatch):
        from app.services.auth_service import InvalidGoogleTokenError, verify_google_id_token

        for bad in (None, "", "not-an-email"):
            _fake_claims(monkeypatch, email=bad)
            with pytest.raises(InvalidGoogleTokenError):
                verify_google_id_token("t")

    def test_wraps_library_errors(self, google_enabled, monkeypatch):
        """token ผิดหรือเครือข่ายล่ม ต้องกลายเป็น error เดียวกัน ไม่รั่วรายละเอียดภายใน"""
        from app.services.auth_service import InvalidGoogleTokenError, verify_google_id_token

        def boom(token, request, audience):
            raise ValueError("Token expired")

        monkeypatch.setattr("google.oauth2.id_token.verify_oauth2_token", boom)
        with pytest.raises(InvalidGoogleTokenError):
            verify_google_id_token("t")

    def test_normalizes_email(self, google_enabled, monkeypatch):
        from app.services.auth_service import verify_google_id_token

        _fake_claims(monkeypatch, email="  MiXeD.Case@Example.COM  ")
        assert verify_google_id_token("t") == "mixed.case@example.com"


class TestAuthConfigEndpoint:
    """หน้าเว็บอ่านค่านี้ตอนทำงานเพื่อรู้ว่าจะแสดงปุ่ม Google หรือไม่"""

    def test_reports_null_when_disabled(self, client):
        resp = client.get("/api/v1/auth/config")
        assert resp.status_code == 200
        assert resp.json() == {"google_client_id": None}

    def test_reports_client_id_when_enabled(self, client, google_enabled):
        assert client.get("/api/v1/auth/config").json() == {"google_client_id": CLIENT_ID}

    def test_does_not_expose_other_settings(self, client, google_enabled):
        """ต้องมีแค่คีย์เดียว กันการเผลอส่ง admin_token หรือ encryption_key ออกไป"""
        assert set(client.get("/api/v1/auth/config").json()) == {"google_client_id"}


class TestGoogleSignInEndpoint:
    def test_disabled_returns_503(self, client):
        resp = _google(client, accept_privacy_policy=True)
        assert resp.status_code == 503
        assert resp.headers["X-Auth-Reason"] == "GOOGLE_DISABLED"

    def test_creates_account_on_first_sign_in(self, client, google_enabled, monkeypatch):
        _fake_claims(monkeypatch)
        resp = _google(client, accept_privacy_policy=True)
        assert resp.status_code == 201
        body = resp.json()
        assert body["token"]
        assert body["user"]["email"] == "somchai.google@example.com"
        # ต้องมีหลักฐานความยินยอมเหมือนบัญชีที่สมัครด้วยรหัสผ่าน
        assert body["user"]["consent_version"] == settings.privacy_policy_version

        with SessionLocal() as db:
            user = db.query(AppUser).one()
            assert user.password_hash is None, "บัญชีจาก Google ต้องไม่มีรหัสผ่าน"
            assert user.google_linked_at is not None

    def test_new_account_requires_consent(self, client, google_enabled, monkeypatch):
        """ความยินยอมต้องชัดแจ้ง การกดปุ่ม Google ไม่นับเป็นการยอมรับนโยบาย"""
        _fake_claims(monkeypatch)
        resp = _google(client)
        assert resp.status_code == 400
        assert resp.headers["X-Auth-Reason"] == "CONSENT_REQUIRED"
        with SessionLocal() as db:
            assert db.query(AppUser).count() == 0

    def test_second_sign_in_reuses_account(self, client, google_enabled, monkeypatch):
        _fake_claims(monkeypatch)
        assert _google(client, accept_privacy_policy=True).status_code == 201
        again = _google(client)      # ไม่ต้องยอมรับนโยบายซ้ำ และไม่ต้องสร้างบัญชีใหม่
        assert again.status_code == 200
        with SessionLocal() as db:
            assert db.query(AppUser).count() == 1

    def test_does_not_store_plaintext_email(self, client, google_enabled, monkeypatch):
        """ข้อกำหนดเดียวกับบัญชีที่สมัครด้วยรหัสผ่าน: ห้ามมีอีเมลเป็นข้อความธรรมดา"""
        _fake_claims(monkeypatch)
        _google(client, accept_privacy_policy=True)
        with SessionLocal() as db:
            user = db.query(AppUser).one()
            assert "somchai.google" not in user.email_hash
            assert "somchai.google" not in user.email_encrypted


class TestLinkingExistingPasswordAccount:
    """
    ป้องกัน pre-registration takeover

    ระบบยังไม่มีการยืนยันอีเมลตอนสมัคร ใครก็สมัครอีเมลของคนอื่นไว้ก่อนได้
    Google sign-in จึงต้องขอรหัสผ่านเดิมก่อนผูก ไม่ใช่เข้าบัญชีนั้นได้เลย
    """

    def test_requires_password_before_linking(self, client, google_enabled, monkeypatch):
        assert _register(client).status_code == 201
        _fake_claims(monkeypatch)

        resp = _google(client)
        assert resp.status_code == 409
        assert resp.headers["X-Auth-Reason"] == "PASSWORD_REQUIRED_TO_LINK"
        # ต้องยังไม่ผูก และต้องไม่ออก session ให้
        assert "token" not in resp.json()
        with SessionLocal() as db:
            assert db.query(AppUser).one().google_linked_at is None

    def test_wrong_password_does_not_link(self, client, google_enabled, monkeypatch):
        _register(client)
        _fake_claims(monkeypatch)

        resp = _google(client, link_password="wrong-password")
        assert resp.status_code == 401
        assert resp.headers["X-Auth-Reason"] == "INVALID_LINK_PASSWORD"
        with SessionLocal() as db:
            assert db.query(AppUser).one().google_linked_at is None

    def test_correct_password_links_once(self, client, google_enabled, monkeypatch):
        _register(client)
        _fake_claims(monkeypatch)

        linked = _google(client, link_password=PASSWORD)
        assert linked.status_code == 200
        assert linked.json()["token"]
        with SessionLocal() as db:
            user = db.query(AppUser).one()
            assert user.google_linked_at is not None
            assert user.password_hash is not None, "รหัสผ่านเดิมต้องยังใช้ได้"

        # ผูกแล้วไม่ต้องกรอกรหัสผ่านอีก
        assert _google(client).status_code == 200
        # และยังเข้าสู่ระบบด้วยรหัสผ่านได้เหมือนเดิม
        pwd_login = client.post("/api/v1/auth/login", json={"email": GOOGLE_EMAIL, "password": PASSWORD})
        assert pwd_login.status_code == 200


class TestDeleteGoogleAccount:
    def test_google_user_can_delete_with_fresh_token(self, client, google_enabled, monkeypatch):
        """บัญชีจาก Google ไม่มีรหัสผ่าน ถ้ายืนยันด้วย token ไม่ได้จะลบบัญชีตัวเองไม่ได้เลย"""
        _fake_claims(monkeypatch)
        token = _google(client, accept_privacy_policy=True).json()["token"]

        resp = client.request(
            "DELETE", "/api/v1/auth/me", headers=_auth(token), json={"id_token": "fresh-token"}
        )
        assert resp.status_code == 204
        with SessionLocal() as db:
            assert db.query(AppUser).count() == 0

    def test_password_alone_cannot_delete_google_account(self, client, google_enabled, monkeypatch):
        """password_hash เป็น None ต้องตอบ 403 ไม่ใช่พังเป็น 500"""
        _fake_claims(monkeypatch)
        token = _google(client, accept_privacy_policy=True).json()["token"]

        resp = client.request(
            "DELETE", "/api/v1/auth/me", headers=_auth(token), json={"password": "anything"}
        )
        assert resp.status_code == 403
        with SessionLocal() as db:
            assert db.query(AppUser).count() == 1

    def test_token_of_another_google_account_cannot_delete(self, client, google_enabled, monkeypatch):
        """token ต้องเป็นของบัญชีที่กำลังเข้าสู่ระบบอยู่ ไม่ใช่บัญชี Google ใดก็ได้"""
        _fake_claims(monkeypatch)
        token = _google(client, accept_privacy_policy=True).json()["token"]

        _fake_claims(monkeypatch, email="someone.else@example.com")
        resp = client.request(
            "DELETE", "/api/v1/auth/me", headers=_auth(token), json={"id_token": "other-token"}
        )
        assert resp.status_code == 403
        with SessionLocal() as db:
            assert db.query(AppUser).count() == 1

    def test_delete_requires_some_proof(self, client, google_enabled, monkeypatch):
        _fake_claims(monkeypatch)
        token = _google(client, accept_privacy_policy=True).json()["token"]
        resp = client.request("DELETE", "/api/v1/auth/me", headers=_auth(token), json={})
        assert resp.status_code == 422
