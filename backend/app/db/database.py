from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from app.config import settings

engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """FastAPI dependency: ให้ session ต่อ 1 request แล้วปิดอัตโนมัติ"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
