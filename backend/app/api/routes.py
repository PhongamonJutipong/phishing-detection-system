import time
import json
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.schemas import EmailAnalyzeRequest, EmailAnalyzeResponse, HighlightSpan
from app.ml.model_service import get_model_service, PhishingModelService
from app.db.database import get_db
from app.db.models import EmailLog

router = APIRouter(prefix="/api/v1", tags=["phishing-detection"])


@router.post("/analyze", response_model=EmailAnalyzeResponse)
def analyze_email(
    request: EmailAnalyzeRequest,
    db: Session = Depends(get_db),
    model: PhishingModelService = Depends(get_model_service),
):
    start = time.perf_counter()

    content_hash = EmailLog.make_hash(request.subject or "", request.body)
    existing = db.query(EmailLog).filter(EmailLog.content_hash == content_hash).first()

    if existing:
        # เคยวิเคราะห์อีเมลนี้แล้ว -> คืนผลเดิมทันที (UC-01 ข้อ 7.2) ไม่ต้องเรียกโมเดลซ้ำ
        elapsed_ms = (time.perf_counter() - start) * 1000
        highlights = json.loads(existing.highlighted_terms or "[]")
        return EmailAnalyzeResponse(
            risk_score=existing.risk_score,
            risk_percentage=round(existing.risk_score * 100, 2),
            is_phishing=existing.is_phishing,
            highlights=[HighlightSpan(**h) for h in highlights],
            processing_time_ms=round(elapsed_ms, 2),
        )

    result = model.predict(request.subject or "", request.body)
    elapsed_ms = (time.perf_counter() - start) * 1000

    # บันทึกผลลง PostgreSQL (UC-01 ข้อ 8) เพื่อใช้เป็น cache และข้อมูลสำหรับวิเคราะห์ในอนาคต
    log_entry = EmailLog(
        content_hash=content_hash,
        subject_preview=(request.subject or "")[:255],
        sender=request.sender,
        risk_score=result["risk_score"],
        is_phishing=result["is_phishing"],
        highlighted_terms=json.dumps(result["highlights"], ensure_ascii=False),
        processing_time_ms=elapsed_ms,
    )
    db.add(log_entry)
    db.commit()

    return EmailAnalyzeResponse(
        risk_score=result["risk_score"],
        risk_percentage=round(result["risk_score"] * 100, 2),
        is_phishing=result["is_phishing"],
        highlights=[HighlightSpan(**h) for h in result["highlights"]],
        processing_time_ms=round(elapsed_ms, 2),
    )


@router.get("/health")
def health_check():
    return {"status": "ok"}


@router.get("/model-info")
def model_info(model: PhishingModelService = Depends(get_model_service)):
    """
    คืน metadata ของโมเดลที่กำลังใช้งานอยู่จริง (เทรนเมื่อไหร่, ด้วย metric อะไร)
    มีไว้เพื่อ debug ตอน deploy จริง — ไม่ต้อง SSH เข้าเครื่องไปเปิดไฟล์ json ดูเอง
    """
    if not model.metadata:
        return {"available": False, "message": "โมเดลนี้เทรนก่อนมี model_metadata.json (โมเดลรุ่นเก่า)"}
    return {"available": True, **model.metadata}
