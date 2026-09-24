"""
ตารางฐานข้อมูลตามแผนภาพความสัมพันธ์ของข้อมูล (รูปที่ 3.10) และพจนานุกรมข้อมูล (ตารางที่ 3.9-3.14)

  email (1) ── (M) detection_result (M) ── (1) detection_model
  email (1) ── (M) tokenized_word   (1) ── (M) tfidf_feature
  email (1) ── (M) feature_vector
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, Date, DateTime, Double, ForeignKey, Integer, Numeric, String, Text, Uuid
from sqlalchemy.orm import relationship

from app.db.database import Base


def _utcnow():
    return datetime.now(timezone.utc)


class Email(Base):
    """ตารางที่ 3.9 พจนานุกรมข้อมูลตารางข้อมูลอีเมล (Email)"""
    __tablename__ = "email"

    email_id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    receive_time = Column(DateTime(timezone=True), nullable=True, default=_utcnow)
    # HMAC-SHA256 ของเนื้อหาอีเมล ใช้ตรวจว่า "เคยพบเนื้อหาอีเมลชุดนี้หรือไม่" (UC-04 ข้อ 6)
    # ใช้ HMAC แทน SHA-256 ธรรมดา เพื่อไม่ให้ผู้ที่มีสำเนาอีเมลอยู่แล้วนำมาแฮชเทียบ
    # ว่าอีเมลฉบับนั้นเคยผ่านระบบหรือไม่ได้ (ดู DatabaseManager.make_body_hash)
    body_hash = Column(String(255), nullable=False, unique=True, index=True)
    # เนื้อหาอีเมลที่เข้ารหัสแล้วด้วย DatabaseManager.encrypt() (Class DatabaseManager)
    # จะเป็น None เมื่อ STORE_EMAIL_CONTENT=false ซึ่งเป็นค่าเริ่มต้น
    body_encrypted = Column(Text, nullable=True)
    # กำหนดวันหมดอายุของข้อมูลตั้งแต่ตอนบันทึก เพื่อให้ลบทิ้งได้ตาม DATA_RETENTION_DAYS
    # None = ไม่มีกำหนดลบ (เมื่อตั้ง DATA_RETENTION_DAYS=0)
    expires_at = Column(DateTime(timezone=True), nullable=True, index=True)

    results = relationship("DetectionResult", back_populates="email", cascade="all, delete-orphan")
    tokens = relationship("TokenizedWord", back_populates="email", cascade="all, delete-orphan")
    features = relationship("FeatureVector", back_populates="email", cascade="all, delete-orphan")


class DetectionModel(Base):
    """ตารางที่ 3.10 พจนานุกรมข้อมูลตารางข้อมูลโมเดลที่ใช้ตรวจจับ (Detection Model)"""
    __tablename__ = "detection_model"

    model_id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    model_name = Column(String(100), nullable=True)
    algorithm = Column(String(100), nullable=True)
    accuracy = Column(Numeric(5, 2), nullable=True)   # ร้อยละ เช่น 95.12
    train_date = Column(Date, nullable=True)

    results = relationship("DetectionResult", back_populates="model")


class DetectionResult(Base):
    """ตารางที่ 3.11 พจนานุกรมข้อมูลตารางผลการตรวจจับและวิเคราะห์ (detection_result)"""
    __tablename__ = "detection_result"

    result_id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    phishing_probability = Column(Numeric(5, 4), nullable=True)
    classification = Column(String(50), nullable=True)
    scan_time = Column(DateTime(timezone=True), nullable=True, default=_utcnow)
    email_id = Column(Uuid, ForeignKey("email.email_id"), nullable=False, index=True)
    model_id = Column(Uuid, ForeignKey("detection_model.model_id"), nullable=False, index=True)

    email = relationship("Email", back_populates="results")
    model = relationship("DetectionModel", back_populates="results")


class TokenizedWord(Base):
    """ตารางที่ 3.12 พจนานุกรมข้อมูลตารางข้อมูลคำศัพท์ที่ผ่านการตัดคำ (tokenized_word)"""
    __tablename__ = "tokenized_word"

    token_id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    frequency = Column(Integer, nullable=True)
    word = Column(String(50), nullable=True)
    email_id = Column(Uuid, ForeignKey("email.email_id"), nullable=False, index=True)

    email = relationship("Email", back_populates="tokens")
    tfidf_features = relationship("TfidfFeature", back_populates="token", cascade="all, delete-orphan")


class TfidfFeature(Base):
    """ตารางที่ 3.13 พจนานุกรมข้อมูลตารางค่าคุณลักษณะทางสถิติของคำ (TF-IDF)"""
    __tablename__ = "tfidf_feature"

    tfidf_id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    tf_value = Column(Double, nullable=True)
    idf_value = Column(Double, nullable=True)
    tfidf_score = Column(Double, nullable=True)
    token_id = Column(Uuid, ForeignKey("tokenized_word.token_id"), nullable=False, index=True)

    token = relationship("TokenizedWord", back_populates="tfidf_features")


class FeatureVector(Base):
    """ตารางที่ 3.14 พจนานุกรมข้อมูลตารางชุดข้อมูลเวกเตอร์คุณลักษณะ (feature_vector)"""
    __tablename__ = "feature_vector"

    vector_id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    feature_name = Column(String(255), nullable=True)
    feature_value = Column(Double, nullable=True)
    email_id = Column(Uuid, ForeignKey("email.email_id"), nullable=False, index=True)

    email = relationship("Email", back_populates="features")


# ---------------------------------------------------------------------------
# บัญชีผู้ใช้ — เพิ่มภายหลัง ไม่อยู่ในพจนานุกรมข้อมูลบทที่ 3
#
# ผลการตรวจอีเมลข้างบนไม่ผูกกับบัญชีผู้ใช้โดยตั้งใจ ถ้าผูกไว้ ผู้ที่อ่านฐานข้อมูลได้
# จะรู้ว่าใครได้รับอีเมลแบบไหน ซึ่งเกินกว่าที่ระบบต้องรู้เพื่อตรวจฟิชชิง
# ---------------------------------------------------------------------------

class AppUser(Base):
    """
    บัญชีผู้ใช้ เก็บเท่าที่จำเป็นต่อการเข้าสู่ระบบเท่านั้น (ไม่เก็บชื่อ เบอร์โทร หรือ IP)

    ชื่อตารางเป็น app_user เพราะ user เป็นคำสงวนของ PostgreSQL
    """
    __tablename__ = "app_user"

    user_id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    # HMAC-SHA256 ของอีเมล (ตัวพิมพ์เล็ก) ใช้ค้นหาตอนเข้าสู่ระบบโดยไม่ต้องเก็บอีเมลเป็นข้อความธรรมดา
    email_hash = Column(String(64), nullable=False, unique=True, index=True)
    # อีเมลที่เข้ารหัส Fernet ไว้แสดงให้เจ้าของบัญชีดู ถอดได้เฉพาะเซิร์ฟเวอร์ที่มี ENCRYPTION_KEY
    email_encrypted = Column(Text, nullable=False)
    # scrypt พร้อม salt สุ่มต่อบัญชี รูปแบบ scrypt$n$r$p$salt$hash
    password_hash = Column(String(255), nullable=False)
    # หลักฐานความยินยอม: ยอมรับนโยบายความเป็นส่วนตัวฉบับไหน เมื่อไร
    consent_version = Column(String(20), nullable=False)
    consent_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)

    sessions = relationship("UserSession", back_populates="user", cascade="all, delete-orphan")


class UserSession(Base):
    """การเข้าสู่ระบบที่ยังใช้งานอยู่ ลบแถวทิ้งเมื่อออกจากระบบ หมดอายุ หรือลบบัญชี"""
    __tablename__ = "user_session"

    session_id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    # SHA-256 ของ token เก็บแค่ค่าแฮช ถ้าฐานข้อมูลรั่วก็นำไปสวมรอยเข้าสู่ระบบไม่ได้
    token_hash = Column(String(64), nullable=False, unique=True, index=True)
    user_id = Column(Uuid, ForeignKey("app_user.user_id", ondelete="CASCADE"), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)

    user = relationship("AppUser", back_populates="sessions")
