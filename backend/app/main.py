import re
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.auth_routes import router as auth_router
from app.api.routes import router
from app.config import settings
from app.core.logger import logger
from app.db import models  # noqa: F401  (ลงทะเบียนตารางทั้งหมดกับ Base.metadata)
from app.db.database import SessionLocal, engine
from app.db.database_manager import DatabaseManager
from app.ml.model_registry import get_model_registry
from app.nlp.nlp_process import NLPProcess


@asynccontextmanager
async def lifespan(app: FastAPI):
    # โครงสร้างฐานข้อมูลเป็นหน้าที่ของ Alembic ไม่ใช่ create_all()
    # เพราะ create_all สร้างเฉพาะตารางที่ยังไม่มี แต่ไม่เคย ALTER ตารางเดิม
    # ถ้าเพิ่มคอลัมน์ใน models.py แล้วพึ่ง create_all ระบบจะขึ้นได้ตามปกติ
    # แล้วไปพังตอนเขียนข้อมูลแทน ซึ่งหาสาเหตุยากกว่ามาก
    #   - ใน container: entrypoint รัน alembic upgrade head ให้ก่อนเริ่มเซิร์ฟเวอร์
    #   - รันบนเครื่อง: สั่ง python -m alembic upgrade head เองจากโฟลเดอร์ backend
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1 FROM alembic_version"))
    except Exception:
        logger.log_warning(
            "ยังไม่พบตาราง alembic_version — ฐานข้อมูลอาจยังไม่ได้ทำ migration "
            "ให้สั่ง 'python -m alembic upgrade head' จากโฟลเดอร์ backend ก่อนใช้งาน"
        )

    get_model_registry()  # โหลดโมเดลครั้งเดียวตอนเริ่มระบบ

    # อุ่นเครื่องตัวตัดคำภาษาไทย: การสร้างคลังคำ (Trie) ครั้งแรกใช้เวลาประมาณ 0.5 วินาที
    # ถ้าไม่ทำตรงนี้ ผู้ใช้คนแรกจะเจอ request ที่ช้ากว่าปกติมาก
    try:
        NLPProcess().tokenize("ทดสอบระบบ warm up")
    except Exception as exc:
        logger.log_warning(f"อุ่นเครื่องตัวตัดคำไม่สำเร็จ: {exc}")

    # ลบข้อมูลที่เลยกำหนดเก็บตั้งแต่ตอนเริ่มระบบ
    # เซิร์ฟเวอร์ที่รันค้างยาวจะไม่ได้ลบเพิ่มเอง ให้ตั้ง cron เรียก POST /api/v1/data/purge เป็นรอบ ๆ
    if settings.data_retention_days > 0:
        try:
            with SessionLocal() as db:
                DatabaseManager(db).purge_expired()
        except Exception as exc:
            logger.log_warning(f"ลบข้อมูลหมดอายุตอนเริ่มระบบไม่สำเร็จ: {exc}")

    logger.log_info("Phishing Detection API started")
    yield


app = FastAPI(
    title="Phishing Email Detection API",
    description="ระบบตรวจจับอีเมลฟิชชิงโดยใช้ NLP + Naive Bayes สำหรับส่วนขยายเว็บเบราว์เซอร์",
    version="1.0.0",
    lifespan=lifespan,
)


def _split_cors_origins(raw: str) -> tuple[list[str], str | None]:
    """
    แยกค่า CORS_ORIGINS ออกเป็น exact-match origins กับ regex สำหรับ origin ที่มี wildcard (*)
    เพราะ Starlette CORSMiddleware ไม่รองรับ "*" กลางสตริงใน allow_origins
    """
    origins = [o.strip() for o in raw.split(",") if o.strip()]
    exact = [o for o in origins if "*" not in o]
    wildcard = [o for o in origins if "*" in o]

    regex = None
    if wildcard:
        regex = "|".join(f"^{re.escape(o).replace(re.escape('*'), '.*')}$" for o in wildcard)
    return exact, regex


_exact_origins, _origin_regex = _split_cors_origins(settings.cors_origins)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_exact_origins,
    allow_origin_regex=_origin_regex,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "X-Admin-Token"],
)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    # การจัดการข้อผิดพลาด (บทที่ 1.5.2): บันทึก log และตอบกลับแบบไม่เปิดเผยรายละเอียดภายใน
    logger.log_error(f"{request.method} {request.url.path}: {exc!r}")
    return JSONResponse(status_code=500, content={"detail": "เกิดข้อผิดพลาดภายในระบบ", "code": "INTERNAL_ERROR"})


app.include_router(router)
app.include_router(auth_router)


@app.get("/api")
def api_root():
    return {"message": "Phishing Detection API is running", "docs": "/docs", "web": "/"}


class SpaStaticFiles(StaticFiles):
    """
    เสิร์ฟไฟล์ที่มีอยู่จริง ถ้าไม่มีให้คืน index.html แทน

    หน้าเว็บเป็น Angular ที่ใช้ routing แบบ path เช่น /scan และ /dashboard
    ซึ่งไม่มีไฟล์จริงอยู่บนดิสก์ ถ้าผู้ใช้กดรีเฟรชหรือเปิดลิงก์ตรงเข้ามาที่ /scan
    เซิร์ฟเวอร์ต้องคืน index.html แล้วให้ Angular อ่าน URL เองแล้วแสดงหน้าที่ถูกต้อง
    ไม่เช่นนั้นจะได้ 404 ทั้งที่หน้านั้นมีอยู่ในแอป
    """

    async def get_response(self, path: str, scope):
        # StaticFiles "โยน" HTTPException(404) ออกมา ไม่ได้คืน response ที่มี status 404
        # จึงต้องดักที่ exception ไม่ใช่ตรวจ status_code ของค่าที่คืนมา
        try:
            return await super().get_response(path, scope)
        except StarletteHTTPException as exc:
            if exc.status_code == 404:
                return await super().get_response("index.html", scope)
            raise


# หน้าเว็บ Angular เสิร์ฟจาก origin เดียวกับ API จึงไม่ต้องตั้งค่าที่อยู่เซิร์ฟเวอร์และไม่ติด CORS
# ต้อง mount ท้ายสุด เพราะ path "/" จะรับทุก path ที่ route อื่นไม่ได้จับไว้ก่อนแล้ว
WEB_DIR = Path(__file__).parent / "web"
if (WEB_DIR / "index.html").is_file():
    app.mount("/", SpaStaticFiles(directory=WEB_DIR, html=True), name="web")
else:
    logger.log_warning(
        f"ไม่พบหน้าเว็บที่ {WEB_DIR} — ให้บริการเฉพาะ API "
        "(สั่ง 'npm run build' ในโฟลเดอร์ frontend เพื่อสร้างหน้าเว็บ)"
    )
