from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator

MAX_BODY_LENGTH = 100_000


class EmailAnalyzeRequest(BaseModel):
    """ข้อมูลอีเมลในรูปแบบเจสัน จาก Email.getDetails() ของส่วนขยาย (Class Email)"""
    email_id: Optional[str] = Field(default=None, max_length=255, description="รหัสของอีเมลฉบับที่เปิดอยู่ (จาก Gmail)")
    subject: Optional[str] = Field(default="", max_length=1000, description="หัวข้ออีเมล")
    sender: Optional[str] = Field(default=None, max_length=255, description="ชื่อ/ที่อยู่ผู้ส่ง")
    body_content: str = Field(..., max_length=MAX_BODY_LENGTH, description="เนื้อหาอีเมลแบบข้อความล้วน")
    time_stamp: Optional[datetime] = Field(default=None, description="เวลาที่ทำการสแกนอีเมล")

    @field_validator("body_content")
    @classmethod
    def body_must_not_be_blank(cls, value: str) -> str:
        # UC-04 ข้อ 3: เอพีไอตรวจสอบความถูกต้องของข้อมูล
        if not value or not value.strip():
            raise ValueError("body_content ต้องไม่เป็นค่าว่าง")
        return value


RiskLevel = Literal["safe", "suspicious", "dangerous"]


class HighlightTerm(BaseModel):
    phrase: str
    # model_keyword | urgency | credential_request | authority | reward | suspicious_link
    reason: str
    weight: float = 0.0


class Indicator(BaseModel):
    category: str
    phrases: list[str]


class EmailAnalyzeResponse(BaseModel):
    result_id: Optional[str] = None
    risk_score: float                       # 0.0 - 1.0 ความน่าจะเป็นที่เป็นฟิชชิง
    risk_percentage: float                  # 0 - 100 สำหรับแสดงผล
    risk_level: RiskLevel                   # แดง/เหลือง/เขียว (UC-06)
    is_phishing: bool
    classification: Literal["phishing", "legitimate"]
    language: Literal["th", "en"]
    language_scores: dict[str, float]       # ความน่าจะเป็นของแต่ละภาษา (UC-04 ข้อ 9-10)
    highlights: list[HighlightTerm]
    suspicious_keywords: list[str]
    indicators: list[Indicator]
    processing_time_ms: float


class ErrorResponse(BaseModel):
    detail: str
    code: str


# ===== บัญชีผู้ใช้ =====

class RegisterRequest(BaseModel):
    email: str = Field(..., max_length=254)
    password: str = Field(..., min_length=8, max_length=128)
    # ต้องเป็น true เท่านั้น การสมัครคือการยินยอมให้เก็บข้อมูลบัญชี จึงต้องขอความยินยอมก่อนเสมอ
    accept_privacy_policy: bool

    @field_validator("email")
    @classmethod
    def email_must_be_valid(cls, value: str) -> str:
        from app.services.auth_service import is_valid_email, normalize_email

        value = normalize_email(value)
        if not is_valid_email(value):
            raise ValueError("รูปแบบอีเมลไม่ถูกต้อง")
        return value

    @field_validator("accept_privacy_policy")
    @classmethod
    def consent_must_be_given(cls, value: bool) -> bool:
        if not value:
            raise ValueError("ต้องยอมรับนโยบายความเป็นส่วนตัวก่อนสมัครสมาชิก")
        return value


class LoginRequest(BaseModel):
    email: str = Field(..., max_length=254)
    password: str = Field(..., min_length=1, max_length=128)
    remember: bool = False


class DeleteAccountRequest(BaseModel):
    # ขอรหัสผ่านซ้ำ กันคนอื่นที่หยิบเครื่องที่เข้าสู่ระบบค้างไว้มาลบบัญชี
    password: str = Field(..., min_length=1, max_length=128)


class UserProfile(BaseModel):
    """ข้อมูลทั้งหมดที่ระบบเก็บเกี่ยวกับบัญชีนี้ (สิทธิ์ขอเข้าถึงข้อมูลของเจ้าของ)"""
    email: Optional[str]
    created_at: datetime
    consent_version: str
    consent_at: datetime


class AuthResponse(BaseModel):
    token: str
    expires_at: datetime
    user: UserProfile
