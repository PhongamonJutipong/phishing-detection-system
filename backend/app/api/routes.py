from fastapi import APIRouter, Depends, Header, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import settings
from app.core.logger import logger
from app.db.database import get_db
from app.db.database_manager import DatabaseManager
from app.ml.model_registry import ModelRegistry, get_model_registry
from app.schemas import EmailAnalyzeRequest, EmailAnalyzeResponse, ErrorResponse
from app.services.phishing_analyzer import ModelUnavailableError, PhishingAnalyzer

router = APIRouter(prefix="/api/v1", tags=["phishing-detection"])


def require_admin(x_admin_token: str | None = Header(default=None)):
    if not settings.admin_token:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="endpoint นี้ถูกปิดใช้งาน")
    if x_admin_token != settings.admin_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="admin token ไม่ถูกต้อง")


@router.post(
    "/analyze",
    response_model=EmailAnalyzeResponse,
    responses={503: {"model": ErrorResponse}},
)
def analyze_email(
    request: EmailAnalyzeRequest,
    db: Session = Depends(get_db),
    registry: ModelRegistry = Depends(get_model_registry),
):
    """UC-04 Analyze Email: รับเนื้อหาอีเมล (เจสัน) วิเคราะห์ และส่งผลลัพธ์กลับ"""
    analyzer = PhishingAnalyzer(registry, DatabaseManager(db))
    try:
        return analyzer.process_request(request)
    except ModelUnavailableError as exc:
        logger.log_error(f"analyze: {exc}")
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"detail": "โหลดโมเดลไม่สำเร็จ ระบบยังไม่พร้อมวิเคราะห์", "code": "MODEL_UNAVAILABLE"},
        )


@router.get("/health")
def health_check(db: Session = Depends(get_db), registry: ModelRegistry = Depends(get_model_registry)):
    database_ok = True
    try:
        db.execute(text("SELECT 1"))
    except Exception as exc:
        database_ok = False
        logger.log_error(f"health: เชื่อมต่อฐานข้อมูลไม่ได้: {exc}")
    models = sorted(registry.available())
    return {
        "status": "ok" if models and database_ok else "degraded",
        "models_loaded": models,
        "database": "ok" if database_ok else "unavailable",
    }


@router.get("/model-info")
def model_info(registry: ModelRegistry = Depends(get_model_registry)):
    """metadata ของโมเดลแต่ละภาษาที่กำลังใช้งานอยู่จริง (เทรนเมื่อไหร่, metric อะไร)"""
    models = registry.available()
    return {
        "available": bool(models),
        "models": {lang: model.metadata for lang, model in models.items()},
    }


@router.post("/model/reload", dependencies=[Depends(require_admin)])
def reload_models(registry: ModelRegistry = Depends(get_model_registry)):
    """โหลดโมเดลรุ่นใหม่จาก MODEL_DIR โดยไม่ต้องรีสตาร์ตเซิร์ฟเวอร์ (การอัปเดตโมเดลอัตโนมัติ บทที่ 3.1.5)"""
    loaded = registry.load_all()
    logger.log_info(f"reload models: {sorted(loaded)}")
    return {"models_loaded": sorted(loaded)}


@router.get("/stats", dependencies=[Depends(require_admin)])
def stats(db: Session = Depends(get_db)):
    """getFeedbackData(): สถิติการตรวจจับสำหรับประเมินประสิทธิภาพของโมเดล"""
    return DatabaseManager(db).get_feedback_data()
