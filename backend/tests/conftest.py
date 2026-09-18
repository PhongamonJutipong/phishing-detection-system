"""
เตรียม environment ก่อนรัน test ของ backend:
1. เติม repo root + backend/ เข้า sys.path ให้ import `app` และ `common` ได้
2. ใช้ SQLite ไฟล์ชั่วคราวแทน PostgreSQL จริง, กุญแจเข้ารหัสชั่วคราว, log ลง temp
3. เทรนโมเดล TF-IDF + Naive Bayes ขนาดเล็กของจริง (ภาษาอังกฤษ + ไทย) ลงโฟลเดอร์ชั่วคราว
   เพื่อทดสอบ pipeline ทั้งหมดโดยไม่ต้องมีไฟล์โมเดลจริงจาก ml/train.py
"""
import json
import os
import sys
import tempfile
from pathlib import Path

_BACKEND_DIR = Path(__file__).resolve().parents[1]
_REPO_ROOT = _BACKEND_DIR.parent
for _p in (_REPO_ROOT, _BACKEND_DIR):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from cryptography.fernet import Fernet  # noqa: E402

_TMP = Path(tempfile.mkdtemp(prefix="phishing_backend_test_"))
os.environ["DATABASE_URL"] = f"sqlite:///{_TMP / 'test.db'}"
os.environ["ENCRYPTION_KEY"] = Fernet.generate_key().decode()
os.environ["LOG_FILE"] = str(_TMP / "test.log")
os.environ["MODEL_DIR"] = str(_TMP / "no_models_here")
os.environ["ADMIN_TOKEN"] = "test-admin-token"

import joblib  # noqa: E402
import pytest  # noqa: E402
from sklearn.feature_extraction.text import TfidfVectorizer  # noqa: E402
from sklearn.naive_bayes import MultinomialNB  # noqa: E402

from common.text_cleaning import clean_text  # noqa: E402

TRAINING_DATA = {
    "en": [
        ("Urgent: your account has been suspended. Verify your identity immediately at http://secure-login.com", 1),
        ("Your password will expire today, click here to confirm your password and credit card", 1),
        ("Congratulations winner! Claim your prize now, provide your bank account details", 1),
        ("Security alert: unusual sign in, verify account within 24 hours or it will be deleted", 1),
        ("Hi team, attaching the minutes from today's meeting. See you next week", 0),
        ("Reminder: project report is due on Friday, please upload it to the shared folder", 0),
        ("Thanks for lunch yesterday, let's catch up again soon", 0),
        ("The seminar schedule for next semester has been posted on the department website", 0),
    ],
    "th": [
        ("แจ้งเตือนด่วน บัญชีของคุณถูกระงับ กรุณายืนยันตัวตนทันทีที่ http://verify-login.com", 1),
        ("กรุณากรอกรหัสผ่านและเลขบัตรเครดิตภายใน 24 ชั่วโมง มิฉะนั้นบัญชีจะถูกปิดถาวร", 1),
        ("ยินดีด้วย คุณได้รับรางวัล คลิกที่นี่เพื่อรับเงินคืนภาษี", 1),
        ("ธนาคารตรวจพบการเข้าสู่ระบบผิดปกติ กรุณายืนยันตัวตนและรหัสผ่าน", 1),
        ("เรียนนักศึกษาทุกท่าน ขอแจ้งกำหนดการสอบกลางภาคประจำภาคเรียนนี้", 0),
        ("ขอเชิญประชุมคณะกรรมการในวันพุธ เวลา 9 โมงเช้า ที่ห้องประชุมชั้น 3", 0),
        ("ส่งเอกสารรายงานความก้าวหน้าโครงงานภายในวันศุกร์นี้นะครับ", 0),
        ("ขอบคุณสำหรับความร่วมมือในการจัดกิจกรรมเมื่อสัปดาห์ที่ผ่านมา", 0),
    ],
}


@pytest.fixture(scope="session")
def model_dir() -> Path:
    root = _TMP / "ml_model"
    for lang, rows in TRAINING_DATA.items():
        texts = [clean_text(text) for text, _ in rows]
        labels = [label for _, label in rows]
        vectorizer = TfidfVectorizer(ngram_range=(1, 2), token_pattern=r"(?u)[^\s]+", lowercase=False, sublinear_tf=True)
        X = vectorizer.fit_transform(texts)
        model = MultinomialNB(alpha=0.1).fit(X, labels)
        out = root / lang
        out.mkdir(parents=True, exist_ok=True)
        joblib.dump(vectorizer, out / "tfidf_vectorizer.pkl")
        joblib.dump(model, out / "naive_bayes_model.pkl")
        (out / "model_metadata.json").write_text(
            json.dumps({"language": lang, "trained_at_utc": "2026-01-01T00:00:00+00:00", "metrics": {"accuracy": 1.0}}),
            encoding="utf-8",
        )
    return root


@pytest.fixture()
def registry(model_dir):
    from app.ml.model_registry import ModelRegistry

    reg = ModelRegistry(str(model_dir))
    reg.load_all()
    return reg


@pytest.fixture()
def client(registry):
    from fastapi.testclient import TestClient

    from app.db.database import Base, engine
    from app.main import app
    from app.ml.model_registry import get_model_registry

    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    app.dependency_overrides[get_model_registry] = lambda: registry
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
