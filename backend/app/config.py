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

    # ===== ความเป็นส่วนตัวของข้อมูล =====
    # ค่าเริ่มต้นทั้งหมดในกลุ่มนี้ตั้งไว้แบบ "ปลอดภัยที่สุดก่อน" (privacy by default)
    # การเปิดใช้งานแต่ละตัวคือการเลือกเก็บข้อมูลส่วนบุคคลเพิ่ม ต้องมีเหตุผลรองรับเสมอ

    # เก็บเนื้อหาอีเมล (เข้ารหัส Fernet) ลงฐานข้อมูลหรือไม่
    store_email_content: bool = False

    # เก็บคำที่ตัดได้ ค่า TF-IDF และเวกเตอร์คุณลักษณะ "รายอีเมล" หรือไม่
    #
    # คำเตือน: ข้อมูลชุดนี้เก็บคำของอีเมลเป็นข้อความธรรมดาผูกกับ email_id
    # ผู้ที่อ่านฐานข้อมูลได้สามารถประกอบเนื้อหาอีเมลกลับได้ แม้ body_encrypted จะเข้ารหัสไว้
    # เปิดเฉพาะตอนเก็บข้อมูลเพื่อทำวิจัยและต้องแจ้งผู้ใช้ให้ทราบ ห้ามเปิดบนระบบจริง
    store_nlp_artifacts: bool = False

    # ลบข้อมูลที่เก่ากว่ากี่วัน (0 = ไม่ลบอัตโนมัติ)
    data_retention_days: int = 90

    # กุญแจสำหรับทำ HMAC ของ body_hash เพื่อไม่ให้ผู้อื่นนำอีเมลที่มีอยู่มาแฮชเทียบ
    # ว่าเคยผ่านระบบหรือไม่ได้ ว่างไว้จะใช้ encryption_key แทน
    hash_pepper: str = ""

    # จำกัดจำนวนคำขอต่อ IP ต่อนาทีสำหรับ POST /analyze (0 = ไม่จำกัด)
    analyze_rate_limit_per_minute: int = 60
    # ขนาดสูงสุดของตาราง rate limit ในหน่วยความจำ กัน memory โตไม่จำกัด
    rate_limit_max_clients: int = 10000

    # ===== บัญชีผู้ใช้ =====
    # รุ่นของนโยบายความเป็นส่วนตัวที่ผู้สมัครกดยอมรับ บันทึกคู่กับบัญชีเป็นหลักฐานความยินยอม
    # เปลี่ยนค่านี้ทุกครั้งที่แก้เนื้อหานโยบาย จะได้รู้ว่าแต่ละคนยินยอมกับฉบับไหน
    privacy_policy_version: str = "2026-09-24"
    # อายุของการเข้าสู่ระบบ: แบบปกติสั้น เพื่อลดความเสี่ยงเมื่อลืมออกจากระบบบนเครื่องสาธารณะ
    session_hours: int = 12
    # เมื่อเลือก "จดจำการเข้าสู่ระบบ"
    session_remember_days: int = 30
    # จำกัดคำขอสมัคร/เข้าสู่ระบบต่อ IP ต่อนาที กันการสุ่มเดารหัสผ่าน (0 = ไม่จำกัด)
    auth_rate_limit_per_minute: int = 10

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
