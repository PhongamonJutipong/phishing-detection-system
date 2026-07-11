# Build context ต้องเป็น repo root (phishing-detection-system/) ไม่ใช่ backend/
# เพราะต้อง COPY โฟลเดอร์ common/ (ใช้ร่วมกับ ml/) เข้า image ด้วย
# ตัวอย่างคำสั่ง build ตรง ๆ (ปกติใช้ผ่าน docker-compose แทน):
#   docker build -f backend/Dockerfile -t phishing-backend .
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

WORKDIR /app

# ติดตั้ง dependencies ก่อนแยกจาก layer โค้ด เพื่อให้ Docker cache layer นี้ไว้
# (โค้ดเปลี่ยนบ่อยกว่า dependencies มาก การเรียงแบบนี้ทำให้ build รอบถัด ๆ ไปเร็วขึ้นมาก)
COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

# common/ ต้องมาก่อน เพราะ backend/app/ml/preprocessing.py import จากตรงนี้
COPY common/ ./common/
COPY backend/app/ ./app/

# ไฟล์โมเดล .pkl (ถ้ามีตอน build) — โปรดักชันจริงควรอัปโหลด/mount แยกแทนการฝังใน image
COPY backend/ml_model/ ./ml_model/

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/v1/health')" || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
