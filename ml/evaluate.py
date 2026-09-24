"""
เปรียบเทียบ 5 อัลกอริทึม (SVM, Random Forest, Logistic Regression, Naive Bayes, KNN)
ด้วยตัวชี้วัด 6 ค่า ตามบทที่ 3.3.3: accuracy, precision, recall, F1, เวลาเรียนรู้, เวลาทำนาย

รัน: python evaluate.py [--lang en th]
ผลลัพธ์: ml/results/algorithm_comparison_<lang>.csv
"""
import argparse
import time
from pathlib import Path

import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score
from sklearn.naive_bayes import MultinomialNB
from sklearn.neighbors import KNeighborsClassifier
from sklearn.svm import LinearSVC

from train import NB_ALPHA, PROCESSED_DIR, build_vectorizer

RESULTS_DIR = Path(__file__).parent / "results"


def algorithms() -> dict:
    """
    5 อัลกอริทึมที่นำมาเปรียบเทียบตามบทที่ 3.3.3

    SVM ใช้ LinearSVC ไม่ใช่ SVC(kernel="linear")
    ทั้งสองตัวคืออัลกอริทึมเดียวกัน แต่คนละไลบรารีเบื้องหลัง
      - SVC ใช้ libsvm ซึ่งมีความซับซ้อนประมาณ O(n^2) ถึง O(n^3)
        บนข้อมูล 39,000 แถวจะใช้เวลาหลายชั่วโมงหรือไม่จบเลย
      - LinearSVC ใช้ liblinear ซึ่งออกแบบมาสำหรับข้อมูลจำนวนมากและเบาบาง (sparse)
        แบบเวกเตอร์ TF-IDF โดยเฉพาะ ใช้เวลาระดับวินาที
    เดิมยังตั้ง probability=True ไว้ด้วยทั้งที่โค้ดเรียกแค่ predict() ไม่เคยใช้ค่าความน่าจะเป็น
    ซึ่งทำให้ SVC ต้องทำ cross-validation ภายในเพื่อ Platt scaling เสียเวลาเพิ่มอีกหลายเท่าโดยเปล่าประโยชน์
    """
    return {
        "SVM": LinearSVC(random_state=42, dual="auto"),
        "RandomForest": RandomForestClassifier(n_estimators=200, random_state=42, n_jobs=-1),
        "LogisticRegression": LogisticRegression(max_iter=1000),
        "NaiveBayes": MultinomialNB(alpha=NB_ALPHA),
        "KNN": KNeighborsClassifier(n_neighbors=5),
    }


def evaluate_language(lang: str) -> pd.DataFrame | None:
    data_dir = PROCESSED_DIR / lang
    if not (data_dir / "train.csv").exists():
        print(f"[ข้าม {lang}] ไม่พบข้อมูล — รัน preprocess.py ก่อน")
        return None

    train_df = pd.read_csv(data_dir / "train.csv")
    test_df = pd.read_csv(data_dir / "test.csv")
    vectorizer = build_vectorizer(len(train_df))  # ให้ min_df ตรงกับโมเดลที่ train.py สร้างจริง
    X_train = vectorizer.fit_transform(train_df["clean_text"].fillna(""))
    X_test = vectorizer.transform(test_df["clean_text"].fillna(""))
    y_train, y_test = train_df["label"], test_df["label"]

    rows = []
    for name, clf in algorithms().items():
        t0 = time.perf_counter()
        clf.fit(X_train, y_train)
        train_time = time.perf_counter() - t0

        t0 = time.perf_counter()
        y_pred = clf.predict(X_test)
        predict_time = time.perf_counter() - t0

        rows.append({
            "algorithm": name,
            "accuracy": accuracy_score(y_test, y_pred),
            "precision": precision_score(y_test, y_pred, zero_division=0),
            "recall": recall_score(y_test, y_pred, zero_division=0),
            "f1_score": f1_score(y_test, y_pred, zero_division=0),
            "train_time_sec": train_time,
            "predict_time_sec": predict_time,
        })
        print(f"[{lang}] เทรนและทดสอบเสร็จ: {name}")

    result = pd.DataFrame(rows).sort_values("accuracy", ascending=False)
    RESULTS_DIR.mkdir(exist_ok=True)
    out = RESULTS_DIR / f"algorithm_comparison_{lang}.csv"
    result.to_csv(out, index=False)
    print(f"\n=== [{lang}] ตารางเปรียบเทียบ 5 อัลกอริทึม ===")
    print(result.to_string(index=False, float_format=lambda v: f"{v:.4f}"))
    print(f"บันทึกไว้ที่ {out}")
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--lang", nargs="+", default=["en", "th"])
    args = parser.parse_args()
    for lang in args.lang:
        evaluate_language(lang)


if __name__ == "__main__":
    main()
