"""
Class Config (แผนภาพคลาส รูปที่ 3.2) — ฝั่ง backend

เก็บค่าการตั้งค่าของระบบ อ่านจาก environment / .env และมีเมธอด get_config(key)
สำหรับดึงค่าตามคีย์เพื่อนำไปใช้ในคลาสอื่น
"""
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # protected_namespaces=() ปิด warning ของ pydantic เรื่อง field ขึ้นต้นด้วย "model_" (model_dir เป็นค่าของเราเอง)
    model_config = SettingsConfigDict(env_file=".env", protected_namespaces=())

    database_url: str = "postgresql://phishing_user:phishing_pass@localhost:5432/phishing_db"

    # โฟลเดอร์โมเดล: แยกตามภาษา ml_model/en/ และ ml_model/th/ (UC-04 ข้อ 9-11)
    model_dir: str = str(Path(__file__).parent.parent / "ml_model")

    # MIN_RISK_THRESHOLD: ความน่าจะเป็น >= ค่านี้ ถือว่าเป็นฟิชชิง (ระดับสีแดง "อันตราย")
    min_risk_threshold: float = 0.5
    # ความน่าจะเป็น >= ค่านี้ (แต่ต่ำกว่า min_risk_threshold) = ระดับสีเหลือง "มีโอกาสเสี่ยง"
    suspicious_threshold: float = 0.3
    # ภาษาใดมีสัดส่วนตัวอักษรอย่างน้อยเท่านี้ จึงจะส่งให้โมเดลภาษานั้นวิเคราะห์
    min_language_ratio: float = 0.15
    # จำนวนคำเสี่ยงสูงสุดที่ส่งกลับไปไฮไลต์
    max_highlight_terms: int = 15

    # encryptionKey ของ DatabaseManager (Fernet key แบบ urlsafe base64 32 ไบต์)
    # สร้างด้วย: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    encryption_key: str = ""
    # เก็บเนื้อหาอีเมล (เข้ารหัสแล้ว) ลงฐานข้อมูลหรือไม่ — ปิดได้เพื่อความเป็นส่วนตัว
    store_email_content: bool = True

    # Logger
    log_file: str = str(Path(__file__).parent.parent / "logs" / "backend.log")
    log_level: str = "INFO"

    # token สำหรับ endpoint ผู้ดูแลระบบ (reload โมเดล / ดูสถิติ) — ว่าง = ปิด endpoint เหล่านั้น
    admin_token: str = ""

    # คั่นด้วย comma ได้หลายค่า เช่น "chrome-extension://*,https://myapp.com"
    # ค่าที่มี "*" จะถูกแปลงเป็น regex ใน main.py
    cors_origins: str = "chrome-extension://*,https://mail.google.com"


settings = Settings()


def get_config(key: str, default=None):
    """getConfig(key) ตามแผนภาพคลาส — รับได้ทั้งตัวพิมพ์เล็ก/ใหญ่ เช่น 'MIN_RISK_THRESHOLD'"""
    return getattr(settings, key.lower(), default)
