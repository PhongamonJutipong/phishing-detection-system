from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    database_url: str = "postgresql://phishing_user:phishing_pass@localhost:5432/phishing_db"
    model_dir: str = str(Path(__file__).parent.parent / "ml_model")
    risk_threshold: float = 0.5   # ความน่าจะเป็น >= ค่านี้ ถือว่าเป็นฟิชชิง

    # คั่นด้วย comma ได้หลายค่า เช่น "chrome-extension://*,https://myapp.com"
    # ค่าที่มี "*" จะถูกแปลงเป็น regex ใน main.py (allow_origins แบบ list เฉย ๆ
    # ไม่รองรับ wildcard จริง — ดูคอมเมนต์ใน main.py)
    cors_origins: str = "chrome-extension://*"

    class Config:
        env_file = ".env"
        # ปิด warning ของ pydantic v2 เรื่อง field ชื่อขึ้นต้นด้วย "model_" ชนกับ
        # protected namespace ภายในของมันเอง (ที่นี่ "model_dir" เป็นแค่ config
        # ของเรา ไม่เกี่ยวกับฟีเจอร์ model_* ของ pydantic)
        protected_namespaces = ()


settings = Settings()
