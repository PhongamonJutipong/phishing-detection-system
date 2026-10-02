"""
บัญชีผู้ใช้: สมัครสมาชิก เข้าสู่ระบบ ออกจากระบบ และลบบัญชี

หลักความเป็นส่วนตัวที่ใช้
- เก็บเท่าที่จำเป็น: อีเมล รหัสผ่าน และบันทึกความยินยอม ไม่เก็บชื่อ เบอร์โทร หรือ IP
- ไม่มีอีเมลเป็นข้อความธรรมดาในฐานข้อมูล: เก็บ HMAC ไว้ค้นหา และค่าที่เข้ารหัสไว้แสดงให้เจ้าของดู
- รหัสผ่านเก็บเป็น scrypt ที่มี salt สุ่มต่อบัญชี
- token เก็บเฉพาะค่าแฮช
- เข้าสู่ระบบไม่สำเร็จตอบข้อความเดียวกันเสมอ ไม่บอกว่าอีเมลนี้มีบัญชีหรือไม่
- เจ้าของบัญชีลบบัญชีได้เอง ข้อมูลทุกแถวของบัญชีถูกลบทันที
"""
import base64
import hashlib
import hmac
import re
import secrets
from datetime import datetime, timedelta, timezone

from cryptography.fernet import InvalidToken
from sqlalchemy import delete
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import settings
from app.core.logger import logger
from app.db.database_manager import get_cipher
from app.db.models import AppUser, UserSession

# scrypt ใช้หน่วยความจำ 128 * N * r = 16 MB ต่อครั้ง ทำให้การสุ่มเดาด้วย GPU แพงมาก
_SCRYPT_N, _SCRYPT_R, _SCRYPT_P, _SCRYPT_LEN = 2**14, 8, 1, 64
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
MAX_EMAIL_LENGTH = 254
MIN_PASSWORD_LENGTH = 8
# จำกัดความยาวสูงสุดด้วย เพราะรหัสผ่านยาวมากทำให้ scrypt ใช้เวลานานจนกลายเป็นช่องทางยิงถล่มได้
MAX_PASSWORD_LENGTH = 128


class EmailTakenError(Exception):
    pass


class InvalidCredentialsError(Exception):
    pass


class GoogleSignInDisabledError(Exception):
    """ไม่ได้ตั้ง GOOGLE_CLIENT_ID จึงไม่เปิดช่องทางนี้"""


class InvalidGoogleTokenError(Exception):
    """ID token ปลอม หมดอายุ ออกให้แอปอื่น หรืออีเมลยังไม่ได้ยืนยันกับ Google"""


class ConsentRequiredError(Exception):
    """สร้างบัญชีใหม่โดยยังไม่ได้ยอมรับนโยบายความเป็นส่วนตัว — ความยินยอมต้องชัดแจ้งเสมอ"""


class PasswordRequiredToLinkError(Exception):
    """
    อีเมลนี้มีบัญชีแบบรหัสผ่านอยู่แล้วและยังไม่เคยผูกกับ Google

    ระบบยังไม่มีการยืนยันอีเมลตอนสมัคร ใครก็สมัครอีเมลของคนอื่นไว้ก่อนได้
    ถ้าปล่อยให้ Google sign-in เข้าบัญชีนั้นได้เลย เจ้าของอีเมลตัวจริงจะเดินเข้าไป
    ในบัญชีที่คนอื่นตั้งรหัสผ่านไว้ แล้วคนนั้นยังเข้าถึงบัญชีได้ต่อ
    จึงขอรหัสผ่านเดิมหนึ่งครั้งเพื่อพิสูจน์ว่าเป็นคนเดียวกันก่อนผูก
    """


def normalize_email(email: str) -> str:
    return email.strip().lower()


def is_valid_email(email: str) -> bool:
    return len(email) <= MAX_EMAIL_LENGTH and bool(_EMAIL_RE.match(email))


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(
        password.encode("utf-8"), salt=salt, n=_SCRYPT_N, r=_SCRYPT_R, p=_SCRYPT_P, dklen=_SCRYPT_LEN
    )
    b64 = lambda raw: base64.b64encode(raw).decode("ascii")  # noqa: E731
    return f"scrypt${_SCRYPT_N}${_SCRYPT_R}${_SCRYPT_P}${b64(salt)}${b64(digest)}"


def verify_password(password: str, stored: str | None) -> bool:
    # บัญชีที่สร้างจาก Google ยังไม่มีรหัสผ่าน (stored เป็น None) ต้องตอบ False
    # ไม่ใช่โยน exception ไม่งั้นหน้าที่เรียกตรง ๆ เช่นการลบบัญชีจะพังเป็น 500
    if not stored:
        return False
    try:
        scheme, n, r, p, salt, expected = stored.split("$")
        if scheme != "scrypt":
            return False
        expected_bytes = base64.b64decode(expected)
        digest = hashlib.scrypt(
            password.encode("utf-8"), salt=base64.b64decode(salt),
            n=int(n), r=int(r), p=int(p), dklen=len(expected_bytes),
        )
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(digest, expected_bytes)


# ใช้ตอนไม่พบอีเมล เพื่อให้เวลาตอบกลับเท่ากับกรณีรหัสผ่านผิด
# ไม่อย่างนั้นผู้โจมตีจับเวลาแล้วรู้ได้ว่าอีเมลไหนมีบัญชี
_DUMMY_HASH = hash_password(secrets.token_urlsafe(16))


def email_lookup_hash(email: str) -> str:
    """HMAC ของอีเมล ใช้ค้นหาบัญชี ใส่คำนำหน้าไว้ไม่ให้ซ้ำกับ HMAC ประเภทอื่นของระบบ"""
    pepper = settings.hash_pepper or settings.encryption_key
    payload = f"app_user.email|{normalize_email(email)}".encode("utf-8")
    if not pepper:
        logger.log_warning(
            "ไม่ได้ตั้ง HASH_PEPPER หรือ ENCRYPTION_KEY — email_hash จะเป็น SHA-256 ธรรมดา "
            "ซึ่งผู้อื่นนำรายชื่ออีเมลมาแฮชเทียบได้ ควรตั้งค่าก่อนใช้งานจริง"
        )
        return hashlib.sha256(payload).hexdigest()
    return hmac.new(pepper.encode("utf-8"), payload, hashlib.sha256).hexdigest()


def _token_hash(token: str) -> str:
    # token สุ่ม 256 บิตอยู่แล้ว เดาไม่ได้ จึงใช้ SHA-256 ธรรมดาได้โดยไม่ต้องมีกุญแจ
    return hashlib.sha256(token.encode("ascii")).hexdigest()


# แยกเป็นฟังก์ชันเดี่ยวเพื่อให้เทสต์แทนที่ด้วยตัวตรวจปลอมได้ โดยไม่ต้องยิงจริงไปที่ Google
def verify_google_id_token(raw_token: str) -> str:
    """
    ตรวจ ID token จาก Google แล้วคืนอีเมลที่ยืนยันแล้ว

    google-auth ตรวจลายเซ็นกับ public key ของ Google, ตรวจ iss, aud และวันหมดอายุให้ครบ
    เราตรวจเพิ่มเองว่า email_verified เป็นจริง เพราะ token ที่ลายเซ็นถูกต้องแต่เจ้าของ
    ยังไม่ยืนยันอีเมลกับ Google ใช้เป็นหลักฐานความเป็นเจ้าของอีเมลไม่ได้

    ต้องออกเน็ตได้เพื่อดึง public key (google-auth แคชให้ตามอายุที่ Google กำหนด)
    """
    if not settings.google_client_id:
        raise GoogleSignInDisabledError()

    # import ตรงนี้ไม่ใช่ด้านบนไฟล์ เพื่อให้ระบบที่ไม่ได้เปิดใช้ Google ไม่ต้องโหลด library
    from google.auth.transport import requests as google_requests
    from google.oauth2 import id_token as google_id_token

    try:
        claims = google_id_token.verify_oauth2_token(
            raw_token, google_requests.Request(), settings.google_client_id
        )
    except Exception as exc:
        # ครอบกว้างโดยตั้งใจ: ValueError จาก token ผิด, ข้อผิดพลาดเครือข่ายตอนดึงกุญแจ
        # ไม่ว่ากรณีใดก็ตอบเหมือนกันหมด ไม่ส่งรายละเอียดภายในออกไปให้ผู้เรียก
        logger.log_warning(f"ตรวจ Google ID token ไม่ผ่าน: {type(exc).__name__}")
        raise InvalidGoogleTokenError() from exc

    if not claims.get("email_verified"):
        logger.log_warning("Google ID token ผ่านลายเซ็นแต่ email_verified ไม่เป็นจริง")
        raise InvalidGoogleTokenError()

    email = normalize_email(claims.get("email") or "")
    if not is_valid_email(email):
        raise InvalidGoogleTokenError()
    return email


class AuthService:
    def __init__(self, db: Session):
        self.db = db

    def register(self, email: str, password: str) -> AppUser:
        email = normalize_email(email)
        now = datetime.now(timezone.utc)
        user = AppUser(
            email_hash=email_lookup_hash(email),
            email_encrypted=get_cipher().encrypt(email.encode("utf-8")).decode("ascii"),
            password_hash=hash_password(password),
            consent_version=settings.privacy_policy_version,
            consent_at=now,
            created_at=now,
        )
        self.db.add(user)
        try:
            self.db.commit()
        except IntegrityError as exc:
            self.db.rollback()
            raise EmailTakenError() from exc
        # log เฉพาะ user_id ห้ามมีอีเมลหรือรหัสผ่านใน log
        logger.log_info(f"สมัครสมาชิกใหม่ user_id={user.user_id}")
        return user

    def authenticate(self, email: str, password: str) -> AppUser:
        user = self.db.query(AppUser).filter(AppUser.email_hash == email_lookup_hash(email)).first()
        if user is None:
            verify_password(password, _DUMMY_HASH)
            raise InvalidCredentialsError()
        if not verify_password(password, user.password_hash):
            raise InvalidCredentialsError()
        return user

    def sign_in_with_google(
        self, email: str, accept_privacy_policy: bool = False, link_password: str | None = None
    ) -> tuple[AppUser, bool]:
        """
        เข้าสู่ระบบด้วยอีเมลที่ Google ยืนยันแล้ว คืน (บัญชี, เป็นบัญชีที่เพิ่งสร้างหรือไม่)

        ผู้เรียกต้องตรวจ ID token มาก่อนแล้ว เมธอดนี้รับเฉพาะอีเมลที่ยืนยันแล้วเท่านั้น
        ห้ามเรียกด้วยอีเมลที่ผู้ใช้พิมพ์เอง ไม่งั้นใครก็สวมรอยเป็นเจ้าของอีเมลใดก็ได้

        สามกรณี
          1. ยังไม่มีบัญชี          -> สร้างใหม่ ไม่มีรหัสผ่าน (ต้องยอมรับนโยบายก่อน)
          2. มีบัญชีที่ผูก Google แล้ว -> เข้าสู่ระบบได้เลย
          3. มีบัญชีแบบรหัสผ่าน ยังไม่ผูก -> ขอรหัสผ่านเดิมหนึ่งครั้งเพื่อพิสูจน์ตัวตน
        """
        email = normalize_email(email)
        now = datetime.now(timezone.utc)
        user = self.db.query(AppUser).filter(AppUser.email_hash == email_lookup_hash(email)).first()

        if user is None:
            if not accept_privacy_policy:
                raise ConsentRequiredError()
            user = AppUser(
                email_hash=email_lookup_hash(email),
                email_encrypted=get_cipher().encrypt(email.encode("utf-8")).decode("ascii"),
                password_hash=None,
                google_linked_at=now,
                consent_version=settings.privacy_policy_version,
                consent_at=now,
                created_at=now,
            )
            self.db.add(user)
            try:
                self.db.commit()
            except IntegrityError as exc:
                # มีคนสมัครอีเมลเดียวกันแทรกเข้ามาระหว่างนี้พอดี
                self.db.rollback()
                raise EmailTakenError() from exc
            logger.log_info(f"สร้างบัญชีจากการเข้าสู่ระบบด้วย Google user_id={user.user_id}")
            return user, True

        if user.google_linked_at is None and user.password_hash:
            if link_password is None:
                raise PasswordRequiredToLinkError()
            if not verify_password(link_password, user.password_hash):
                raise InvalidCredentialsError()
            user.google_linked_at = now
            self.db.commit()
            logger.log_info(f"ผูกบัญชีเดิมเข้ากับ Google user_id={user.user_id}")
            return user, False

        if user.google_linked_at is None:
            # บัญชีไม่มีทั้งรหัสผ่านและการผูก (ไม่ควรเกิด) ถือว่า Google พิสูจน์ความเป็นเจ้าของแล้ว
            user.google_linked_at = now
            self.db.commit()
        return user, False

    def create_session(self, user: AppUser, remember: bool = False) -> tuple[str, datetime]:
        now = datetime.now(timezone.utc)
        lifetime = (
            timedelta(days=settings.session_remember_days) if remember
            else timedelta(hours=settings.session_hours)
        )
        # เก็บกวาด session ที่หมดอายุไปพร้อมกัน จะได้ไม่มีแถวค้างสะสม
        self.db.execute(delete(UserSession).where(UserSession.expires_at <= now))
        token = secrets.token_urlsafe(32)
        expires_at = now + lifetime
        self.db.add(UserSession(token_hash=_token_hash(token), user_id=user.user_id, created_at=now, expires_at=expires_at))
        self.db.commit()
        return token, expires_at

    def user_for_token(self, token: str) -> AppUser | None:
        session = (
            self.db.query(UserSession)
            .filter(UserSession.token_hash == _token_hash(token), UserSession.expires_at > datetime.now(timezone.utc))
            .first()
        )
        return session.user if session else None

    def revoke_session(self, token: str) -> None:
        self.db.execute(delete(UserSession).where(UserSession.token_hash == _token_hash(token)))
        self.db.commit()

    def decrypt_email(self, user: AppUser) -> str | None:
        """None เมื่อถอดไม่ได้ เช่น ENCRYPTION_KEY ถูกเปลี่ยนหลังสมัคร (บัญชียังเข้าสู่ระบบได้ตามปกติ)"""
        try:
            return get_cipher().decrypt(user.email_encrypted.encode("ascii")).decode("utf-8")
        except (InvalidToken, ValueError):
            logger.log_warning(f"ถอดรหัสอีเมลของ user_id={user.user_id} ไม่ได้ — ENCRYPTION_KEY อาจถูกเปลี่ยน")
            return None

    def delete_account(self, user: AppUser) -> None:
        """ลบบัญชีและการเข้าสู่ระบบทั้งหมดของบัญชีนั้นทันที ไม่มีการเก็บสำเนาไว้"""
        user_id = user.user_id
        # ลบ session ก่อนเอง เพราะ SQLite ไม่บังคับ ON DELETE CASCADE ถ้าไม่เปิด foreign_keys
        self.db.execute(delete(UserSession).where(UserSession.user_id == user_id))
        self.db.execute(delete(AppUser).where(AppUser.user_id == user_id))
        self.db.commit()
        logger.log_info(f"ลบบัญชีตามคำขอของเจ้าของ user_id={user_id}")
