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
from sklearn.model_selection import StratifiedKFold, cross_validate
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import Pipeline

PROCESSED_DIR = Path(__file__).parent / "data" / "processed"
MODEL_OUT_DIR = Path(__file__).parent.parent / "backend" / "ml_model"

# ค่าด้านล่างมาจากการทดลองบนชุดข้อมูลจริงภาษาอังกฤษ 39,320 แถว
# (ดูตารางเปรียบเทียบท้ายไฟล์ README ของ ml/ และ ml/results/)
#
# VECTORIZER_MAX_FEATURES: เดิมตั้งไว้ 20000 ตอนที่ชุดข้อมูลมีแค่ 95 แถว ซึ่งไม่เคยถูกแตะเลย
# แต่พอข้อมูลโตเป็นสี่หมื่นแถว เพดานนี้กลายเป็นคอขวดหลัก วัดได้ดังนี้
#   20,000 -> accuracy 0.9027 | 50,000 -> 0.9287 | 100,000 -> 0.9453 | ไม่จำกัด -> 0.9651
# None = ไม่จำกัด แล้วใช้ min_df คุมขนาดคลังคำแทน ซึ่งคัดกรองได้ตรงกว่า
VECTORIZER_MAX_FEATURES = None
VECTORIZER_NGRAM_RANGE = (1, 2)   # bigram สำคัญ ตัดเหลือ unigram accuracy ตกจาก 0.9651 เป็น 0.9343
# min_df=2 ตัดคำที่โผล่ในเอกสารเดียว ซึ่งส่วนใหญ่เป็นคำสะกดผิดหรือเศษข้อมูล
# ลดคลังคำจาก 2.1 ล้านเหลือ 668,000 คำ (ไฟล์โมเดล 129 MB -> 40 MB) โดย accuracy แทบไม่ต่าง
VECTORIZER_MIN_DF = 2
# ใช้ min_df ข้างบนต่อเมื่อมีเอกสารอย่างน้อยเท่านี้ ต่ำกว่านี้ใช้ 1 เพื่อไม่ให้คลังคำหายเกือบหมด
MIN_DOCS_FOR_MIN_DF = 1000
# alpha คือความ "ไม่เชื่อข้อมูล" ยิ่งข้อมูลเยอะยิ่งควรลด
#   1.0 -> 0.9424 | 0.3 -> 0.9563 | 0.1 -> 0.9651 | 0.05 -> 0.9702
NB_ALPHA = 0.05
CV_FOLDS = 5             # จำนวน fold ของ cross-validation
RANDOM_STATE = 42        # ให้ผลซ้ำได้ ตรงกับที่ preprocess.py ใช้แบ่งข้อมูล
ACCURACY_TARGET = 0.85   # สมมติฐานข้อ 1.4.1


def build_vectorizer(n_docs: int | None = None) -> TfidfVectorizer:
    """
    สร้าง TF-IDF vectorizer

    ข้อความผ่าน clean_text() มาแล้ว (ตัดคำ + คั่นด้วยช่องว่าง) จึงแยก token ด้วยช่องว่างเท่านั้น
    เพื่อไม่ให้ตัดคำภาษาไทยซ้ำหรือทิ้งคำยาว 1 ตัวอักษร

    min_df ปรับตามขนาดข้อมูล: การตัดคำที่โผล่ในเอกสารเดียวช่วยลด noise ได้จริง
    เมื่อมีข้อมูลหลักหมื่น แต่ถ้าข้อมูลมีไม่กี่ร้อยแถว คำส่วนใหญ่ย่อมโผล่ครั้งเดียว
    การใช้ min_df=2 จะตัดคลังคำทิ้งเกือบหมดจนโมเดลไม่เหลืออะไรให้เรียนรู้
    """
    min_df = VECTORIZER_MIN_DF if (n_docs or 0) >= MIN_DOCS_FOR_MIN_DF else 1
    return TfidfVectorizer(
        max_features=VECTORIZER_MAX_FEATURES,
        ngram_range=VECTORIZER_NGRAM_RANGE,
        min_df=min_df,
        token_pattern=r"(?u)[^\s]+",
        lowercase=False,
        sublinear_tf=True,
    )


def cross_validate_metrics(texts, labels) -> dict:
    """
    วัดผลด้วย k-fold cross-validation บนข้อมูลทั้งหมด

    สร้าง TF-IDF ใหม่ในทุก fold ผ่าน Pipeline เพื่อไม่ให้คำจากชุดตรวจรั่วเข้าไป
    อยู่ในคลังคำตอนเทรน (ถ้า fit_transform ทั้งก้อนก่อนแบ่ง ผลจะดูดีเกินจริง)
    """
    n_per_class = labels.value_counts().min()
    folds = min(CV_FOLDS, int(n_per_class))
    if folds < 2:
        return {}

    pipeline = Pipeline([("tfidf", build_vectorizer(len(texts))), ("nb", MultinomialNB(alpha=NB_ALPHA))])
    scores = cross_validate(
        pipeline,
        texts,
        labels,
        cv=StratifiedKFold(n_splits=folds, shuffle=True, random_state=RANDOM_STATE),
        scoring=("accuracy", "f1"),
    )
    return {
        "cv_folds": float(folds),
        "cv_accuracy_mean": float(scores["test_accuracy"].mean()),
        "cv_accuracy_std": float(scores["test_accuracy"].std()),
        "cv_f1_mean": float(scores["test_f1"].mean()),
        "cv_f1_std": float(scores["test_f1"].std()),
    }


def train_language(lang: str) -> dict | None:
    data_dir = PROCESSED_DIR / lang
    if not (data_dir / "train.csv").exists():
        print(f"[ข้าม {lang}] ไม่พบ {data_dir / 'train.csv'} — รัน preprocess.py ก่อน")
        return None

    started = time.perf_counter()

    def step(msg: str) -> None:
        print(f"[{lang}] {time.perf_counter() - started:6.1f}s  {msg}")

    step("โหลดข้อมูล")
    train_df = pd.read_csv(data_dir / "train.csv")
    test_df = pd.read_csv(data_dir / "test.csv")
    X_train_text, y_train = train_df["clean_text"].fillna(""), train_df["label"]
    X_test_text, y_test = test_df["clean_text"].fillna(""), test_df["label"]

    step(f"สร้างคลังคำ TF-IDF จาก {len(X_train_text):,} แถว")
    vectorizer = build_vectorizer(len(X_train_text))
    X_train = vectorizer.fit_transform(X_train_text)
    X_test = vectorizer.transform(X_test_text)

    step(f"คลังคำ {len(vectorizer.vocabulary_):,} คำ | เทรน Naive Bayes และวัดผลชุดทดสอบ {len(X_test_text):,} แถว")
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

    # ค่าจากการแบ่ง 80/20 ครั้งเดียวเชื่อถือได้น้อย เพราะชุดทดสอบมีไม่กี่สิบแถว
    # เปลี่ยน random_state ทีก็เด้งได้หลายจุดเปอร์เซ็นต์ จึงวัดซ้ำด้วย k-fold
    # บนข้อมูลทั้งหมดแล้วรายงานค่าเฉลี่ยพร้อมส่วนเบี่ยงเบนมาตรฐานควบคู่กันไป
    # ค่านี้คือค่าที่ควรนำไปใช้รายงานผลตามบทที่ 3.4
    step(f"cross-validation {CV_FOLDS} fold (ขั้นนี้นานที่สุด)")
    cv = cross_validate_metrics(
        pd.concat([X_train_text, X_test_text], ignore_index=True),
        pd.concat([y_train, y_test], ignore_index=True),
    )
    if cv:
        metrics.update(cv)
    step("เสร็จ")

    print(f"\n=== [{lang}] Naive Bayes + TF-IDF ===")
    for k, v in metrics.items():
        print(f"{k:30s}: {v:.4f}")
    print(f"confusion matrix [[TN, FP], [FN, TP]]: {cm}")
    if cv:
        print(
            f"{'cross-validation (' + str(CV_FOLDS) + '-fold)':30s}: "
            f"accuracy {cv['cv_accuracy_mean']:.4f} +/- {cv['cv_accuracy_std']:.4f} | "
            f"f1 {cv['cv_f1_mean']:.4f} +/- {cv['cv_f1_std']:.4f}"
        )

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
