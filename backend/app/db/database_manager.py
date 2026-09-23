"""
Class DatabaseManager (แผนภาพคลาส รูปที่ 3.2)

จัดการฐานข้อมูล PostgreSQL: ตรวจสอบข้อมูลเดิม (checkData), เข้ารหัสเนื้อหาอีเมล (encrypt),
บันทึกประวัติการสแกน (saveSecureLog) และดึงข้อมูลสถิติ (getFeedbackData)
"""
import hashlib
import hmac
import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy import delete, func, insert
from sqlalchemy.exc import IntegrityError
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
        """
        HMAC-SHA256 ของหัวข้อ+เนื้อหา ใช้ตรวจอีเมลซ้ำ

        ใช้ HMAC ที่มีกุญแจแทน SHA-256 ธรรมดา เพราะ SHA-256 ธรรมดาทำให้ผู้ที่มีสำเนา
        อีเมลอยู่แล้ว (เช่น ผู้ส่งสแปมเอง) แฮชอีเมลนั้นแล้วค้นในฐานข้อมูลเพื่อยืนยันว่า
        เป้าหมายเคยเปิดอ่านอีเมลฉบับนั้นหรือไม่ได้ การใส่กุญแจปิดช่องทางนี้
        """
        pepper = settings.hash_pepper or settings.encryption_key
        payload = f"{subject}||{body}".encode("utf-8")
        if not pepper:
            # ไม่มีกุญแจให้ใช้ ยังต้องแฮชได้เพื่อไม่ให้ระบบล่ม แต่ต้องเตือนให้ชัด
            logger.log_warning(
                "ไม่ได้ตั้ง HASH_PEPPER หรือ ENCRYPTION_KEY — body_hash จะเป็น SHA-256 ธรรมดา "
                "ซึ่งผู้อื่นนำอีเมลมาแฮชเทียบได้ ควรตั้งค่าก่อนใช้งานจริง"
            )
            return hashlib.sha256(payload).hexdigest()
        return hmac.new(pepper.encode("utf-8"), payload, hashlib.sha256).hexdigest()

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
                    expires_at=self._expiry_time(),
                    body_encrypted=(
                        self.encrypt(f"{log.get('subject', '')}\n\n{log['body']}")
                        if settings.store_email_content else None
                    ),
                )
                try:
                    # SAVEPOINT: ถ้าคำขออีกเส้นแทรกอีเมลเนื้อหาเดียวกันเข้ามาก่อนในเสี้ยววินาที
                    # เดียวกัน UNIQUE ของ body_hash จะฟ้อง เรายกเลิกเฉพาะ savepoint นี้
                    # แล้วใช้แถวที่อีกเส้นสร้างไว้แทน ธุรกรรมชั้นนอกไม่ถูก abort
                    # (สำคัญบน PostgreSQL ที่ error หนึ่งครั้งทำให้ทั้งธุรกรรมใช้ต่อไม่ได้)
                    with db.begin_nested():
                        db.add(email)
                    self._save_nlp_artifacts(email, log)
                except IntegrityError:
                    email = self.check_data(log["body_hash"])
                    if email is None:
                        raise

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

    @staticmethod
    def _expiry_time() -> datetime | None:
        """เวลาหมดอายุของข้อมูลที่กำลังจะบันทึก (None = เก็บไว้ไม่มีกำหนด)"""
        days = settings.data_retention_days
        if days <= 0:
            return None
        return datetime.now(timezone.utc) + timedelta(days=days)

    def _save_nlp_artifacts(self, email: Email, log: dict) -> None:
        """
        บันทึกคำที่ตัดได้ ค่า TF-IDF และเวกเตอร์คุณลักษณะรายอีเมล

        ปิดไว้เป็นค่าเริ่มต้น เพราะคอลัมน์ word และ feature_name เก็บคำของอีเมล
        เป็นข้อความธรรมดาผูกกับ email_id ผู้ที่อ่านฐานข้อมูลได้จึงประกอบเนื้อหาอีเมล
        กลับมาได้ ทั้งที่ body_encrypted เข้ารหัสไว้แล้ว เปิดเฉพาะตอนเก็บข้อมูลวิจัย
        """
        if not settings.store_nlp_artifacts:
            return

        db = self.db_connection
        # สร้าง token_id ไว้ล่วงหน้า จะได้ผูก tfidf ได้โดยไม่ต้อง flush คั่นกลาง
        token_ids: dict[str, uuid.UUID] = {}
        token_rows = []
        for word, freq in log.get("token_counts", {}).items():
            token_ids[word] = uuid.uuid4()
            token_rows.append({
                "token_id": token_ids[word],
                "word": word[:50],
                "frequency": int(freq),
                "email_id": email.email_id,
            })

        tfidf_rows = [
            {
                "tfidf_id": uuid.uuid4(),
                "tf_value": tf,
                "idf_value": idf,
                "tfidf_score": score,
                "token_id": token_ids[word],
            }
            for word, tf, idf, score in log.get("tfidf_rows", [])
            if word in token_ids
        ]
        feature_rows = [
            {
                "vector_id": uuid.uuid4(),
                "feature_name": str(name)[:255],
                "feature_value": float(value),
                "email_id": email.email_id,
            }
            for name, value in log.get("features", [])
        ]

        # เขียนเป็นชุดด้วย executemany แทนการ add ทีละแถว
        # อีเมลหนึ่งฉบับสร้างได้หลายร้อยแถว การ add ทีละแถวคือเวลาส่วนใหญ่ของคำขอ
        if token_rows:
            db.execute(insert(TokenizedWord), token_rows)
        if tfidf_rows:
            db.execute(insert(TfidfFeature), tfidf_rows)
        if feature_rows:
            db.execute(insert(FeatureVector), feature_rows)

    # ---------- การลบข้อมูลตามกำหนดเก็บ ----------
    def purge_expired(self, batch_size: int = 1000) -> dict:
        """
        ลบข้อมูลที่เลยกำหนดเก็บแล้ว (DATA_RETENTION_DAYS)

        ลบลูกก่อนพ่อแม่ เพราะ ForeignKey ในฐานข้อมูลไม่ได้ตั้ง ON DELETE CASCADE ไว้
        (cascade ที่ประกาศใน models.py เป็นระดับ ORM ซึ่งไม่ทำงานกับคำสั่ง DELETE แบบชุด)
        ทำทีละชุดเพื่อไม่ให้คำสั่ง SQL ยาวเกินไปเมื่อข้อมูลค้างสะสมมาก
        """
        db = self.db_connection
        now = datetime.now(timezone.utc)
        expired_ids = [
            row[0]
            for row in db.query(Email.email_id)
            .filter(Email.expires_at.isnot(None), Email.expires_at <= now)
            .limit(batch_size)
            .all()
        ]
        if not expired_ids:
            return {"deleted_emails": 0, "remaining": 0}

        token_ids = [
            row[0]
            for row in db.query(TokenizedWord.token_id)
            .filter(TokenizedWord.email_id.in_(expired_ids))
            .all()
        ]
        if token_ids:
            db.execute(delete(TfidfFeature).where(TfidfFeature.token_id.in_(token_ids)))
        db.execute(delete(TokenizedWord).where(TokenizedWord.email_id.in_(expired_ids)))
        db.execute(delete(FeatureVector).where(FeatureVector.email_id.in_(expired_ids)))
        db.execute(delete(DetectionResult).where(DetectionResult.email_id.in_(expired_ids)))
        db.execute(delete(Email).where(Email.email_id.in_(expired_ids)))
        db.commit()

        remaining = (
            db.query(func.count(Email.email_id))
            .filter(Email.expires_at.isnot(None), Email.expires_at <= now)
            .scalar()
            or 0
        )
        logger.log_info(f"ลบข้อมูลที่หมดอายุแล้ว {len(expired_ids)} อีเมล คงเหลือรอลบ {remaining}")
        return {"deleted_emails": len(expired_ids), "remaining": remaining}

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
