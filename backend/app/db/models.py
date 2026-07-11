import hashlib
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text

from app.db.database import Base


class EmailLog(Base):
    """
    เก็บผลการวิเคราะห์อีเมลแต่ละฉบับ โดยใช้ content_hash (sha256 ของเนื้อหา)
    เป็นตัวเช็คว่าเคยวิเคราะห์อีเมลนี้มาก่อนหรือไม่ (ตาม UC-01 ข้อ 7.1/7.2)
    หมายเหตุ: จงใจไม่เก็บเนื้อหาอีเมลแบบเต็ม ๆ เพื่อความเป็นส่วนตัวของผู้ใช้งาน
    """
    __tablename__ = "email_logs"

    id = Column(Integer, primary_key=True, index=True)
    content_hash = Column(String(64), unique=True, index=True, nullable=False)
    subject_preview = Column(String(255), nullable=True)   # เก็บแค่บางส่วนไว้ debug
    sender = Column(String(255), nullable=True)
    risk_score = Column(Float, nullable=False)
    is_phishing = Column(Boolean, nullable=False)
    highlighted_terms = Column(Text, nullable=True)  # JSON string ของคำที่ถูกไฮไลต์
    processing_time_ms = Column(Float, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    @staticmethod
    def make_hash(subject: str, body: str) -> str:
        raw = f"{subject}||{body}".encode("utf-8")
        return hashlib.sha256(raw).hexdigest()
