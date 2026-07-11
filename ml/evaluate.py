"""
เปรียบเทียบ 5 อัลกอริทึม (SVM, Random Forest, Logistic Regression, Naive Bayes, KNN)
ตามขั้นตอนในบทที่ 3.3.3 ของเอกสารโครงงาน เพื่อยืนยัน/ทำซ้ำผลการเลือกโมเดล

รัน: python evaluate.py
"""
import time
import pandas as pd
from pathlib import Path
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.svm import SVC
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.naive_bayes import MultinomialNB
from sklearn.neighbors import KNeighborsClassifier
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score

PROCESSED_DIR = Path(__file__).parent / "data" / "processed"

ALGORITHMS = {
    "SVM": SVC(kernel="linear", probability=True),
    "RandomForest": RandomForestClassifier(n_estimators=200, random_state=42),
    "LogisticRegression": LogisticRegression(max_iter=1000),
    "NaiveBayes": MultinomialNB(),
    "KNN": KNeighborsClassifier(n_neighbors=5),
}


def main():
    train_df = pd.read_csv(PROCESSED_DIR / "train.csv")
    test_df = pd.read_csv(PROCESSED_DIR / "test.csv")

    vectorizer = TfidfVectorizer(max_features=20000, ngram_range=(1, 2))
    X_train = vectorizer.fit_transform(train_df["clean_text"].fillna(""))
    X_test = vectorizer.transform(test_df["clean_text"].fillna(""))
    y_train, y_test = train_df["label"], test_df["label"]

    results = []
    for name, clf in ALGORITHMS.items():
        t0 = time.time()
        clf.fit(X_train, y_train)
        train_time = time.time() - t0

        t0 = time.time()
        y_pred = clf.predict(X_test)
        predict_time = (time.time() - t0) / max(len(y_test), 1)

        results.append({
            "algorithm": name,
            "accuracy": accuracy_score(y_test, y_pred),
            "precision": precision_score(y_test, y_pred, zero_division=0),
            "recall": recall_score(y_test, y_pred, zero_division=0),
            "f1_score": f1_score(y_test, y_pred, zero_division=0),
            "train_time_sec": train_time,
            "predict_time_per_email_sec": predict_time,
        })
        print(f"เทรนและทดสอบเสร็จ: {name}")

    results_df = pd.DataFrame(results).sort_values("accuracy", ascending=False)
    print("\n=== ตารางเปรียบเทียบ 5 อัลกอริทึม ===")
    print(results_df.to_string(index=False))
    results_df.to_csv(Path(__file__).parent / "algorithm_comparison.csv", index=False)


if __name__ == "__main__":
    main()
