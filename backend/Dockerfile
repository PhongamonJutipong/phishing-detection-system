# Build context ต้องเป็น repo root (phishing-detection-system/) ไม่ใช่ backend/
# เพราะต้อง COPY โฟลเดอร์ common/ (ใช้ร่วมกับ ml/) เข้า image ด้วย
# ตัวอย่างคำสั่ง build ตรง ๆ (ปกติใช้ผ่าน docker-compose แทน):
#   docker build -f backend/Dockerfile -t phishing-backend .
# ---------- ขั้นที่ 1: build หน้าเว็บ Angular ----------
# แยกเป็นคนละขั้นเพื่อไม่ให้ Node.js และ node_modules (หลายร้อย MB) ติดไปกับ image สุดท้าย
# image ที่ได้จึงมีแต่ไฟล์ static ที่ build เสร็จแล้วเท่านั้น
FROM node:24-slim AS web-builder

# วางไว้ที่ /build/frontend เพื่อจำลองโครงสร้างโฟลเดอร์เดียวกับในโปรเจค
# เพราะ angular.json ตั้ง outputPath เป็น "../backend/app/web" ซึ่งอ้างอิงตำแหน่งสัมพัทธ์
# ผลลัพธ์จึงไปอยู่ที่ /build/backend/app/web
WORKDIR /build/frontend

# ติดตั้ง dependencies ก่อนคัดลอกซอร์ส เพื่อให้ Docker cache layer นี้ไว้
# npm ci ใช้ package-lock.json ตรง ๆ จึงได้เวอร์ชันเดิมทุกครั้งที่ build
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

COPY frontend/ ./
RUN npm run build


# ---------- ขั้นที่ 2: backend ----------
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

WORKDIR /app

# ติดตั้ง dependencies ก่อนแยกจาก layer โค้ด เพื่อให้ Docker cache layer นี้ไว้
# (โค้ดเปลี่ยนบ่อยกว่า dependencies มาก การเรียงแบบนี้ทำให้ build รอบถัด ๆ ไปเร็วขึ้นมาก)
COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

# common/ ต้องมาก่อน เพราะ backend/app/nlp/nlp_process.py import จากตรงนี้
COPY common/ ./common/
COPY backend/app/ ./app/

# หน้าเว็บที่ build เสร็จจากขั้นที่ 1 — ต้องมาหลัง COPY backend/app/ เพราะเขียนทับโฟลเดอร์ web ข้างใน
# ถ้าสลับลำดับ ไฟล์ที่ build ไว้จะถูกของเก่าทับ
COPY --from=web-builder /build/backend/app/web/ ./app/web/

# ไฟล์ migration ต้องอยู่ใน image ด้วย เพราะ entrypoint เรียก alembic upgrade head
# ก่อนเปิดรับคำขอ (โครงสร้างฐานข้อมูลเป็นของ Alembic ไม่ได้สร้างด้วย create_all แล้ว)
COPY backend/alembic.ini ./alembic.ini
COPY backend/alembic/ ./alembic/

COPY backend/docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

# ไฟล์โมเดล .pkl (ถ้ามีตอน build) — โปรดักชันจริงควรอัปโหลด/mount แยกแทนการฝังใน image
COPY backend/ml_model/ ./ml_model/

# รันด้วยผู้ใช้ธรรมดา ไม่ใช่ root — ถ้ามีช่องโหว่ในแอป ผู้โจมตีจะไม่ได้สิทธิ์ root ใน container
RUN mkdir -p /app/logs \
    && useradd --create-home --uid 10001 appuser \
    && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/v1/health')" || exit 1

ENTRYPOINT ["docker-entrypoint.sh"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
