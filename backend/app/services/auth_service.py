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


def verify_password(password: str, stored: str) -> bool:
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
