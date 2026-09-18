"""
เทรนโมเดลสุดท้าย: TF-IDF + Naive Bayes แยกภาษาไทย/อังกฤษ (บทที่ 3.1.5 และ UC-04 ข้อ 9-11)
บันทึก vectorizer + model + model_metadata.json ไว้ที่ backend/ml_model/<lang>/

รัน: python train.py [--lang en th]
"""
import argparse
import json
import platform
import time
from datetime import datetime, timezone
from pathlib import Path

import joblib
import pandas as pd
import sklearn
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score, precision_score, recall_score
from sklearn.naive_bayes import MultinomialNB

PROCESSED_DIR = Path(__file__).parent / "data" / "processed"
MODEL_OUT_DIR = Path(__file__).parent.parent / "backend" / "ml_model"

VECTORIZER_MAX_FEATURES = 20000
VECTORIZER_NGRAM_RANGE = (1, 2)
NB_ALPHA = 0.1
ACCURACY_TARGET = 0.85   # สมมติฐานข้อ 1.4.1


def build_vectorizer() -> TfidfVectorizer:
    # ข้อความผ่าน clean_text() มาแล้ว (ตัดคำ + คั่นด้วยช่องว่าง) จึงแยก token ด้วยช่องว่างเท่านั้น
    # เพื่อไม่ให้ตัดคำภาษาไทยซ้ำ/ทิ้งคำยาว 1 ตัวอักษร
    return TfidfVectorizer(
        max_features=VECTORIZER_MAX_FEATURES,
        ngram_range=VECTORIZER_NGRAM_RANGE,
        token_pattern=r"(?u)[^\s]+",
        lowercase=False,
        sublinear_tf=True,
    )


def train_language(lang: str) -> dict | None:
    data_dir = PROCESSED_DIR / lang
    if not (data_dir / "train.csv").exists():
        print(f"[ข้าม {lang}] ไม่พบ {data_dir / 'train.csv'} — รัน preprocess.py ก่อน")
        return None

    train_df = pd.read_csv(data_dir / "train.csv")
    test_df = pd.read_csv(data_dir / "test.csv")
    X_train_text, y_train = train_df["clean_text"].fillna(""), train_df["label"]
    X_test_text, y_test = test_df["clean_text"].fillna(""), test_df["label"]

    vectorizer = build_vectorizer()
    X_train = vectorizer.fit_transform(X_train_text)
    X_test = vectorizer.transform(X_test_text)

    model = MultinomialNB(alpha=NB_ALPHA)
    t0 = time.perf_counter()
    model.fit(X_train, y_train)
    train_time = time.perf_counter() - t0

    t0 = time.perf_counter()
    y_pred = model.predict(X_test)
    predict_time = time.perf_counter() - t0

    metrics = {
        "accuracy": accuracy_score(y_test, y_pred),
        "precision": precision_score(y_test, y_pred, zero_division=0),
        "recall": recall_score(y_test, y_pred, zero_division=0),
        "f1_score": f1_score(y_test, y_pred, zero_division=0),
        "train_time_sec": train_time,
        "predict_time_sec": predict_time,
        "predict_time_per_email_sec": predict_time / max(len(y_test), 1),
    }
    cm = confusion_matrix(y_test, y_pred, labels=[0, 1]).tolist()

    print(f"\n=== [{lang}] Naive Bayes + TF-IDF ===")
    for k, v in metrics.items():
        print(f"{k:30s}: {v:.4f}")
    print(f"confusion matrix [[TN, FP], [FN, TP]]: {cm}")

    out_dir = MODEL_OUT_DIR / lang
    out_dir.mkdir(parents=True, exist_ok=True)
    joblib.dump(vectorizer, out_dir / "tfidf_vectorizer.pkl")
    joblib.dump(model, out_dir / "naive_bayes_model.pkl")

    metadata = {
        "language": lang,
        "trained_at_utc": datetime.now(timezone.utc).isoformat(),
        "model_type": "TF-IDF + MultinomialNB",
        "nb_alpha": NB_ALPHA,
        "sklearn_version": sklearn.__version__,
        "python_version": platform.python_version(),
        "train_rows": len(train_df),
        "test_rows": len(test_df),
        "vectorizer_max_features": VECTORIZER_MAX_FEATURES,
        "vectorizer_ngram_range": list(VECTORIZER_NGRAM_RANGE),
        "metrics": metrics,
        "confusion_matrix": cm,
    }
    (out_dir / "model_metadata.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"บันทึกโมเดลไว้ที่: {out_dir}")

    if metrics["accuracy"] < ACCURACY_TARGET:
        print(f"[คำเตือน] ค่าความถูกต้อง ({lang}) ต่ำกว่าเกณฑ์ร้อยละ 85 ตามสมมติฐานข้อ 1.4.1")
    return metrics


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--lang", nargs="+", default=["en", "th"])
    args = parser.parse_args()
    results = {lang: train_language(lang) for lang in args.lang}
    if not any(results.values()):
        raise SystemExit("ไม่มีโมเดลใดถูกเทรน")


if __name__ == "__main__":
    main()
