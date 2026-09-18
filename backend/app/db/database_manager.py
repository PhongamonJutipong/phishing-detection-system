"""
Class DatabaseManager (แผนภาพคลาส รูปที่ 3.2)

จัดการฐานข้อมูล PostgreSQL: ตรวจสอบข้อมูลเดิม (checkData), เข้ารหัสเนื้อหาอีเมล (encrypt),
บันทึกประวัติการสแกน (saveSecureLog) และดึงข้อมูลสถิติ (getFeedbackData)
"""
import hashlib
from datetime import date, datetime, timezone
from decimal import Decimal

from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.config import settings
from app.core.logger import logger
from app.db.models import DetectionModel, DetectionResult, Email, FeatureVector, TfidfFeature, TokenizedWord


def _build_cipher(key: str) -> Fernet:
    if key:
        return Fernet(key.encode())
    logger.log_warning(
        "ไม่ได้ตั้งค่า ENCRYPTION_KEY — ใช้กุญแจชั่วคราว (ข้อมูลที่เข้ารหัสจะถอดไม่ได้หลังรีสตาร์ต) "
        "ควรตั้งค่าใน .env สำหรับการใช้งานจริง"
    )
    return Fernet(Fernet.generate_key())


_cipher: Fernet | None = None


def get_cipher() -> Fernet:
    global _cipher
    if _cipher is None:
        _cipher = _build_cipher(settings.encryption_key)
    return _cipher


class DatabaseManager:
    def __init__(self, db_connection: Session, encryption_key: str | None = None):
        self.db_connection = db_connection
        self.encryption_key = encryption_key if encryption_key is not None else settings.encryption_key
        self._cipher = Fernet(self.encryption_key.encode()) if encryption_key else get_cipher()

    # ---------- การเข้ารหัส ----------
    def encrypt(self, data: str) -> str:
        """เข้ารหัสข้อความเนื้อหาอีเมลก่อนเก็บลงฐานข้อมูล"""
        return self._cipher.encrypt(data.encode("utf-8")).decode("ascii")

    def decrypt(self, token: str) -> str | None:
        try:
            return self._cipher.decrypt(token.encode("ascii")).decode("utf-8")
        except (InvalidToken, ValueError):
            return None

    @staticmethod
    def make_body_hash(subject: str, body: str) -> str:
        return hashlib.sha256(f"{subject}||{body}".encode("utf-8")).hexdigest()

    # ---------- checkData ----------
    def check_data(self, body_hash: str) -> Email | None:
        """เช็คว่าเคยพบเนื้อหาอีเมลชุดนี้ในฐานข้อมูลหรือไม่ (UC-04 ข้อ 6 / ทางเลือก 7.1)"""
        return self.db_connection.query(Email).filter(Email.body_hash == body_hash).first()

    # ---------- detection_model ----------
    def get_or_create_model(self, model_name: str, algorithm: str, metadata: dict) -> DetectionModel:
        accuracy = metadata.get("metrics", {}).get("accuracy")
        train_date = None
        trained_at = metadata.get("trained_at_utc")
        if trained_at:
            try:
                train_date = datetime.fromisoformat(trained_at).date()
            except ValueError:
                train_date = None

        query = self.db_connection.query(DetectionModel).filter(DetectionModel.model_name == model_name)
        query = query.filter(DetectionModel.train_date == train_date) if train_date else query
        existing = query.order_by(DetectionModel.train_date.desc()).first()
        if existing:
            return existing

        model = DetectionModel(
            model_name=model_name,
            algorithm=algorithm,
            accuracy=Decimal(str(round(accuracy * 100, 2))) if accuracy is not None else None,
            train_date=train_date or date.today(),
        )
        self.db_connection.add(model)
        self.db_connection.flush()
        return model

    # ---------- saveSecureLog ----------
    def save_secure_log(self, log: dict) -> DetectionResult:
        """
        บันทึกประวัติการสแกน 1 ครั้ง
        log = {
          subject, body, body_hash, language, probability, classification, model (PhishingModel),
          token_counts (Counter), tfidf_rows [(word, tf, idf, tfidf)], features [(name, value)]
        }
        - อีเมลใหม่: บันทึก email (เข้ารหัส) + tokenized_word + tfidf_feature + feature_vector
        - อีเมลที่เคยพบ: ไม่บันทึกเนื้อหาซ้ำ (UC-04 ทางเลือก 7.1) บันทึกเฉพาะ detection_result
        """
        db = self.db_connection
        try:
            email = self.check_data(log["body_hash"])
            if email is None:
                email = Email(
                    body_hash=log["body_hash"],
                    receive_time=datetime.now(timezone.utc),
                    body_encrypted=(
                        self.encrypt(f"{log.get('subject', '')}\n\n{log['body']}")
                        if settings.store_email_content else None
                    ),
                )
                db.add(email)
                db.flush()
                self._save_nlp_artifacts(email, log)

            model = log["model"]
            detection_model = self.get_or_create_model(model.model_name(), "Multinomial Naive Bayes", model.metadata)

            result = DetectionResult(
                phishing_probability=Decimal(str(round(log["probability"], 4))),
                classification=log["classification"],
                scan_time=datetime.now(timezone.utc),
                email_id=email.email_id,
                model_id=detection_model.model_id,
            )
            db.add(result)
            db.commit()
            return result
        except Exception:
            db.rollback()
            raise

    def _save_nlp_artifacts(self, email: Email, log: dict) -> None:
        token_rows = {}
        for word, freq in log.get("token_counts", {}).items():
            row = TokenizedWord(word=word[:50], frequency=int(freq), email_id=email.email_id)
            self.db_connection.add(row)
            token_rows[word] = row
        self.db_connection.flush()

        for word, tf, idf, score in log.get("tfidf_rows", []):
            token = token_rows.get(word)
            if token is None:
                continue
            self.db_connection.add(
                TfidfFeature(tf_value=tf, idf_value=idf, tfidf_score=score, token_id=token.token_id)
            )

        for name, value in log.get("features", []):
            self.db_connection.add(
                FeatureVector(feature_name=name[:255], feature_value=float(value), email_id=email.email_id)
            )

    # ---------- getFeedbackData ----------
    def get_feedback_data(self) -> dict:
        """ดึงข้อมูลสถิติการตรวจจับจากฐานข้อมูล สำหรับวิเคราะห์และประเมินประสิทธิภาพของโมเดล"""
        db = self.db_connection
        total_emails = db.query(func.count(Email.email_id)).scalar() or 0
        total_scans = db.query(func.count(DetectionResult.result_id)).scalar() or 0
        by_class = dict(
            db.query(DetectionResult.classification, func.count(DetectionResult.result_id))
            .group_by(DetectionResult.classification)
            .all()
        )
        models = [
            {
                "model_id": str(m.model_id),
                "model_name": m.model_name,
                "algorithm": m.algorithm,
                "accuracy": float(m.accuracy) if m.accuracy is not None else None,
                "train_date": m.train_date.isoformat() if m.train_date else None,
            }
            for m in db.query(DetectionModel).order_by(DetectionModel.train_date.desc()).all()
        ]
        return {
            "total_emails": total_emails,
            "total_scans": total_scans,
            "scans_by_classification": by_class,
            "models": models,
        }
