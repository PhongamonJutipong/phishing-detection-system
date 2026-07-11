from pydantic import BaseModel, Field
from typing import Optional


class EmailAnalyzeRequest(BaseModel):
    subject: Optional[str] = Field(default="", description="หัวข้ออีเมล")
    body: str = Field(..., description="เนื้อหาอีเมลแบบข้อความล้วน (plain text)")
    sender: Optional[str] = Field(default=None, description="ที่อยู่อีเมลผู้ส่ง (ถ้ามี)")


class HighlightSpan(BaseModel):
    phrase: str
    reason: str  # เช่น "คำที่สื่อถึงความเร่งด่วน", "การขอข้อมูลส่วนบุคคล"


class EmailAnalyzeResponse(BaseModel):
    risk_score: float          # 0.0 - 1.0 ความน่าจะเป็นที่เป็นฟิชชิง
    risk_percentage: float     # 0 - 100 สำหรับแสดงผลใน UI
    is_phishing: bool
    highlights: list[HighlightSpan]
    processing_time_ms: float
