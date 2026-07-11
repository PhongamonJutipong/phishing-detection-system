import re

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.db.database import engine, Base
from app.api.routes import router

# สร้างตารางในฐานข้อมูลอัตโนมัติถ้ายังไม่มี (สำหรับ dev; production ควรใช้ Alembic migration)
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Phishing Email Detection API",
    description="ระบบตรวจจับอีเมลฟิชชิงโดยใช้ NLP + Naive Bayes สำหรับ Chrome Extension",
    version="0.1.0",
)


def _split_cors_origins(raw: str) -> tuple[list[str], str | None]:
    """
    แยกค่า CORS_ORIGINS (คั่นด้วย comma) ออกเป็น exact-match origins กับ regex สำหรับ origin
    ที่มี wildcard (*)

    เหตุผลที่ต้องแยก: Starlette's CORSMiddleware ไม่รองรับ "*" กลางสตริงใน allow_origins
    (รองรับแค่ allow_origins=["*"] แบบ exact ทั้งสตริงเท่านั้น) ถ้าใส่ "chrome-extension://*"
    เข้าไปใน allow_origins ตรง ๆ แบบเดิม จะไม่ match origin ของ extension ที่ส่งมาจริงเลย
    (เงียบ ๆ ไม่มี error แต่ browser จะ block request ด้วย CORS policy) ต้องใช้
    allow_origin_regex แทนสำหรับ pattern ที่มี wildcard
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
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/")
def root():
    return {"message": "Phishing Detection API is running", "docs": "/docs"}
