"""
โหลดโมเดล TF-IDF + Naive Bayes ที่เทรนไว้ล่วงหน้า (จาก ml/train.py)
และให้บริการทำนาย + หาคำ/วลีที่น่าสงสัยสำหรับไฮไลต์ (ตามขอบเขตข้อ 1.5.1)
"""
import json
import re
from pathlib import Path

import joblib

from app.config import settings
from app.ml.preprocessing import clean_text

# กลุ่มคำที่สื่อถึงเทคนิคการโน้มน้าวใจตามทฤษฎีในบทที่ 2.1.1 (Cialdini)
# ใช้เสริมกับน้ำหนักของโมเดลในการอธิบายเหตุผลของการไฮไลต์ให้ผู้ใช้เข้าใจง่ายขึ้น
SUSPICIOUS_PATTERNS = {
    "ความเร่งด่วน": [
        r"ด่วนที่สุด", r"ภายใน\s*\d+\s*(ชั่วโมง|นาที|วัน)", r"immediately", r"urgent",
        r"expire[sd]?", r"suspend(ed)?", r"ระงับ", r"ปิดถาวร",
    ],
    "การขอข้อมูลส่วนบุคคล/รหัสผ่าน": [
        r"รหัสผ่าน", r"password", r"otp", r"เลขบัตร", r"verify.*(account|identity)",
        r"ยืนยันตัวตน", r"credit card", r"บัตรเครดิต",
    ],
    "การแอบอ้างเป็นผู้มีอำนาจ": [
        r"ฝ่ายไอที", r"it department", r"ผู้บริหาร", r"bank", r"ธนาคาร", r"government", r"หน่วยงานรัฐ",
    ],
    "ลิงก์/ไฟล์แนบต้องสงสัย": [r"<url>", r"คลิกที่นี่", r"click here", r"download now"],
}


class PhishingModelService:
    def __init__(self, model_dir: str | None = None):
        model_dir = Path(model_dir or settings.model_dir)
        vectorizer_path = model_dir / "tfidf_vectorizer.pkl"
        model_path = model_dir / "naive_bayes_model.pkl"
        metadata_path = model_dir / "model_metadata.json"

        if not vectorizer_path.exists() or not model_path.exists():
            raise FileNotFoundError(
                f"ไม่พบไฟล์โมเดลใน {model_dir} — รัน `python ml/train.py` ก่อน "
                "แล้วคัดลอกไฟล์ .pkl มาไว้ที่ backend/ml_model/"
            )

        self.vectorizer = joblib.load(vectorizer_path)
        self.model = joblib.load(model_path)

        # metadata เป็น optional (โมเดลรุ่นเก่าก่อนมี field นี้จะไม่มีไฟล์นี้ — ไม่ควร error)
        self.metadata: dict = {}
        if metadata_path.exists():
            self.metadata = json.loads(metadata_path.read_text(encoding="utf-8"))

    def predict(self, subject: str, body: str) -> dict:
        raw_text = f"{subject}. {body}"
        processed = clean_text(raw_text)

        X = self.vectorizer.transform([processed])
        proba = self.model.predict_proba(X)[0]
        # class 1 = ฟิชชิง (ต้องตรงกับ label ตอนเทรน: 1=phishing, 0=normal)
        phishing_idx = list(self.model.classes_).index(1) if 1 in self.model.classes_ else 1
        risk_score = float(proba[phishing_idx])

        highlights = self._find_highlights(raw_text)

        return {
            "risk_score": risk_score,
            "is_phishing": risk_score >= settings.risk_threshold,
            "highlights": highlights,
        }

    @staticmethod
    def _find_highlights(raw_text: str) -> list[dict]:
        """ค้นหาคำ/วลีที่เข้าข่ายน่าสงสัยตามกลุ่มรูปแบบ เพื่อไฮไลต์ให้ผู้ใช้เห็น (ข้อ 1.5.1)"""
        found = []
        lowered = raw_text.lower()
        for reason, patterns in SUSPICIOUS_PATTERNS.items():
            for pattern in patterns:
                match = re.search(pattern, lowered, flags=re.IGNORECASE)
                if match:
                    found.append({"phrase": match.group(0), "reason": reason})
        return found


# instance เดียวใช้ร่วมกันทั้งแอป (โหลดโมเดลครั้งเดียวตอน startup)
model_service: PhishingModelService | None = None


def get_model_service() -> PhishingModelService:
    global model_service
    if model_service is None:
        model_service = PhishingModelService()
    return model_service
