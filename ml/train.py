"""
เทรนโมเดลสุดท้าย: TF-IDF + Naive Bayes (ตามผลการเปรียบเทียบในบทที่ 3.3.3)
บันทึก vectorizer + model ไว้เป็นไฟล์ .pkl สำหรับ backend ใช้งานจริง
พร้อม model_metadata.json บันทึกไว้ข้าง ๆ เพื่อให้รู้ว่าโมเดลที่ deploy อยู่
เทรนเมื่อไหร่ ด้วยข้อมูล/metric อะไร (เดิมไม่มีการบันทึกส่วนนี้เลย ทำให้ตอน
deploy จริงถ้าโมเดลทำนายแปลก ๆ จะสืบไม่ได้ว่ามาจากการเทรนรอบไหน)

รัน: python train.py
"""
import json
import platform
import time
from datetime import datetime, timezone

import joblib
import pandas as pd
import sklearn
from pathlib import Path
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score

PROCESSED_DIR = Path(__file__).parent / "data" / "processed"
MODEL_OUT_DIR = Path(__file__).parent.parent / "backend" / "ml_model"

VECTORIZER_MAX_FEATURES = 20000
VECTORIZER_NGRAM_RANGE = (1, 2)


def main():
    train_df = pd.read_csv(PROCESSED_DIR / "train.csv")
    test_df = pd.read_csv(PROCESSED_DIR / "test.csv")

    X_train_text = train_df["clean_text"].fillna("")
    y_train = train_df["label"]
    X_test_text = test_df["clean_text"].fillna("")
    y_test = test_df["label"]

    # --- TF-IDF ---
    vectorizer = TfidfVectorizer(max_features=VECTORIZER_MAX_FEATURES, ngram_range=VECTORIZER_NGRAM_RANGE)
    X_train = vectorizer.fit_transform(X_train_text)
    X_test = vectorizer.transform(X_test_text)

    # --- เทรนโมเดล ---
    model = MultinomialNB()
    t0 = time.time()
    model.fit(X_train, y_train)
    train_time = time.time() - t0

    # --- ประเมินผล (ตามตัวชี้วัด 6 ค่าในบทที่ 3.3.3) ---
    t0 = time.time()
    y_pred = model.predict(X_test)
    predict_time = (time.time() - t0) / max(len(X_test_text), 1)

    metrics = {
        "accuracy": accuracy_score(y_test, y_pred),
        "precision": precision_score(y_test, y_pred, zero_division=0),
        "recall": recall_score(y_test, y_pred, zero_division=0),
        "f1_score": f1_score(y_test, y_pred, zero_division=0),
        "train_time_sec": train_time,
        "predict_time_per_email_sec": predict_time,
    }

    print("=== ผลการประเมินโมเดล Naive Bayes + TF-IDF ===")
    for k, v in metrics.items():
        print(f"{k:30s}: {v:.4f}")

    # --- บันทึกโมเดล + vectorizer ---
    MODEL_OUT_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(vectorizer, MODEL_OUT_DIR / "tfidf_vectorizer.pkl")
    joblib.dump(model, MODEL_OUT_DIR / "naive_bayes_model.pkl")

    # --- บันทึก metadata สำหรับ traceability ตอน deploy ---
    metadata = {
        "trained_at_utc": datetime.now(timezone.utc).isoformat(),
        "model_type": "TF-IDF + MultinomialNB",
        "sklearn_version": sklearn.__version__,
        "python_version": platform.python_version(),
        "train_rows": len(train_df),
        "test_rows": len(test_df),
        "vectorizer_max_features": VECTORIZER_MAX_FEATURES,
        "vectorizer_ngram_range": list(VECTORIZER_NGRAM_RANGE),
        "metrics": metrics,
    }
    with open(MODEL_OUT_DIR / "model_metadata.json", "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)

    print(f"\nบันทึกโมเดล + model_metadata.json ไว้ที่: {MODEL_OUT_DIR}")

    if metrics["accuracy"] < 0.85:
        print("\n[คำเตือน] ค่าความแม่นยำต่ำกว่าเกณฑ์ 85% ตามสมมติฐานของโครงงาน (ข้อ 1.4.1)")


if __name__ == "__main__":
    main()
