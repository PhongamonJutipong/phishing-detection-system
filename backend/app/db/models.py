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
    # SHA-256 ของเนื้อหาอีเมล ใช้ตรวจว่า "เคยพบเนื้อหาอีเมลชุดนี้หรือไม่" (UC-04 ข้อ 6)
    body_hash = Column(String(255), nullable=False, unique=True, index=True)
    # เนื้อหาอีเมลที่เข้ารหัสแล้วด้วย DatabaseManager.encrypt() (Class DatabaseManager)
    body_encrypted = Column(Text, nullable=True)

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
