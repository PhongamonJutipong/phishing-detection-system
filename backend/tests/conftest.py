"""
เตรียม environment ก่อนรัน test ของ backend:
1. เติม repo root + backend/ เข้า sys.path ให้ import `app` และ `common` ได้
2. สลับ DATABASE_URL ไปใช้ SQLite ไฟล์ชั่วคราวแทน Postgres จริง
   (เดิมถ้าไม่มี Postgres รันอยู่ การ import app.main จะ fail ทันทีเพราะมันเรียก
   Base.metadata.create_all(bind=engine) ตอน import — ทำให้ต้องมี DB จริงถึงจะ
   เขียน/รัน test ได้เลย ซึ่งไม่เหมาะกับ unit test หรือ CI)
"""
import os
import sys
import tempfile
from pathlib import Path

_BACKEND_DIR = Path(__file__).resolve().parents[1]
_REPO_ROOT = _BACKEND_DIR.parent
for _p in (_REPO_ROOT, _BACKEND_DIR):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

_TEST_DB_PATH = Path(tempfile.gettempdir()) / "phishing_backend_test.db"
os.environ["DATABASE_URL"] = f"sqlite:///{_TEST_DB_PATH}"

import pytest  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _cleanup_test_db():
    yield
    _TEST_DB_PATH.unlink(missing_ok=True)
