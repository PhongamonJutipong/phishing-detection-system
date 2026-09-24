from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.config import settings

# SQLite (ใช้ตอนรัน test) ต้องปิด check_same_thread เพราะ FastAPI อาจสร้าง/ปิด session คนละ thread
_connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}

_pool_args = (
    {} if settings.database_url.startswith("sqlite")
    else {"pool_size": settings.db_pool_size, "max_overflow": settings.db_max_overflow}
)

engine = create_engine(settings.database_url, pool_pre_ping=True, connect_args=_connect_args, **_pool_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """FastAPI dependency: ให้ session ต่อ 1 request แล้วปิดอัตโนมัติ"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
