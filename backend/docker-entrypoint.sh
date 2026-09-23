#!/bin/sh
# จุดเริ่มทำงานของ container backend
#
# ต้องอัปเดตโครงสร้างฐานข้อมูลก่อนเปิดรับคำขอเสมอ ไม่เช่นนั้นเมื่อ models.py เปลี่ยน
# แล้ว container ขึ้นมาด้วย schema เก่า ระบบจะพังตอนเขียนข้อมูลแทนที่จะพังตอนเริ่ม
set -e

echo "[entrypoint] รอ PostgreSQL พร้อมรับการเชื่อมต่อ..."
python - <<'PY'
import time
import sqlalchemy
from app.config import settings

engine = sqlalchemy.create_engine(settings.database_url, pool_pre_ping=True)
for attempt in range(1, 31):
    try:
        with engine.connect() as conn:
            conn.execute(sqlalchemy.text("SELECT 1"))
        print(f"[entrypoint] เชื่อมต่อฐานข้อมูลได้ (ครั้งที่ {attempt})")
        break
    except Exception as exc:
        if attempt == 30:
            raise SystemExit(f"[entrypoint] ต่อฐานข้อมูลไม่ได้หลังลอง 30 ครั้ง: {exc}")
        time.sleep(2)
PY

echo "[entrypoint] อัปเดตโครงสร้างฐานข้อมูล (alembic upgrade head)"
alembic upgrade head

echo "[entrypoint] เริ่มเซิร์ฟเวอร์"
exec "$@"
