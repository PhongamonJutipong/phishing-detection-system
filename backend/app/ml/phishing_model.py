"""
Class PhishingModel (แผนภาพคลาส รูปที่ 3.2)

โหลดโมเดล TF-IDF + Naive Bayes ที่บันทึกไว้จาก ml/train.py (หนึ่งชุดต่อหนึ่งภาษา)
โครงสร้างไฟล์:  ml_model/<lang>/tfidf_vectorizer.pkl
                ml_model/<lang>/naive_bayes_model.pkl
                ml_model/<lang>/model_metadata.json
"""
import json
from pathlib import Path

import joblib
import numpy as np

VECTORIZER_FILE = "tfidf_vectorizer.pkl"
MODEL_FILE = "naive_bayes_model.pkl"
METADATA_FILE = "model_metadata.json"
PHISHING_LABEL = 1


class PhishingModel:
    def __init__(self, model_path: str | Path, language: str):
        self.model_path = Path(model_path)
        self.language = language
        self.classifier = None
        self.vectorizer = None
        self.metadata: dict = {}
        # ค่าที่คำนวณครั้งเดียวตอนโหลดโมเดล แทนการคำนวณใหม่ทุกคำขอ (ดู _prepare_fast_path)
        self.feature_names = None
        self._phishing_idx = 0
        self._log_ratio = None

    def load_model(self) -> None:
        """loadModel(): โหลดโมเดลนาอีฟเบย์ + TF-IDF vectorizer (UC-04 ทางเลือก 9.1 ถ้าไม่สำเร็จ)"""
        vectorizer_path = self.model_path / VECTORIZER_FILE
        classifier_path = self.model_path / MODEL_FILE
        if not vectorizer_path.exists() or not classifier_path.exists():
            raise FileNotFoundError(
                f"ไม่พบไฟล์โมเดลภาษา '{self.language}' ใน {self.model_path} — รัน ml/train.py ก่อน"
            )
        self.vectorizer = joblib.load(vectorizer_path)
        self.classifier = joblib.load(classifier_path)

        metadata_path = self.model_path / METADATA_FILE
        if metadata_path.exists():
            self.metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        self._prepare_fast_path()

    def _prepare_fast_path(self) -> None:
        """
        เตรียมค่าที่ใช้ซ้ำทุกคำขอไว้ล่วงหน้า

        get_feature_names_out() สร้างรายการคำศัพท์ทั้งคลังใหม่ทุกครั้งที่เรียก โมเดลอังกฤษมี
        670,000 คำ ใช้เวลาราว 350 ms ต่อครั้ง ซึ่งเคยเป็นเวลาเกือบทั้งหมดของแต่ละคำขอ
        """
        self.feature_names = self.vectorizer.get_feature_names_out()
        classes = list(self.classifier.classes_)
        self._phishing_idx = classes.index(PHISHING_LABEL) if PHISHING_LABEL in classes else len(classes) - 1
        log_prob = getattr(self.classifier, "feature_log_prob_", None)
        if log_prob is not None and log_prob.shape[0] >= 2:
            normal_idx = 1 - self._phishing_idx if log_prob.shape[0] == 2 else 0
            self._log_ratio = log_prob[self._phishing_idx] - log_prob[normal_idx]

    @property
    def is_loaded(self) -> bool:
        return self.classifier is not None and self.vectorizer is not None

    def predict(self, vector) -> dict:
        """
        predict(vector): นำเวกเตอร์ TF-IDF ไปคำนวณความน่าจะเป็นตามทฤษฎีของเบย์
        คืนค่า {"probability": float, "suspicious_terms": [(term, weight), ...]}
        """
        if not self.is_loaded:
            raise RuntimeError(f"โมเดลภาษา '{self.language}' ยังไม่ถูกโหลด")

        row = vector.tocsr()
        return {
            "probability": self._phishing_probability(row),
            "suspicious_terms": self._suspicious_terms(row),
        }

    def _phishing_probability(self, row) -> float:
        """
        P(ฟิชชิง | อีเมล) ตามทฤษฎีของเบย์ สูตรเดียวกับ MultinomialNB.predict_proba ทุกประการ
          log P(c|x) ∝ log P(c) + Σ x_i · log P(คำ_i|c)   แล้ว normalize ด้วย log-sum-exp

        คำนวณเฉพาะคำที่ปรากฏในอีเมล (ส่วนใหญ่ไม่กี่สิบคำ) ข้ามขั้นตรวจสอบข้อมูลของ sklearn
        ที่ไล่ทั้ง 670,000 คอลัมน์ทุกครั้ง เร็วขึ้นหลายสิบเท่า ผลเท่าเดิม (ทดสอบไว้ใน test_components)
        """
        clf = self.classifier
        jll = clf.class_log_prior_ + clf.feature_log_prob_[:, row.indices] @ row.data
        jll = jll - jll.max()
        prob = np.exp(jll)
        return float(prob[self._phishing_idx] / prob.sum())

    def _suspicious_terms(self, row) -> list[tuple[str, float]]:
        """
        หาคำที่ผลักให้โมเดลตัดสินว่าเป็นฟิชชิง: ค่า TF-IDF ของคำ x (log P(คำ|ฟิชชิง) - log P(คำ|ปกติ))
        เลือกเฉพาะคำที่มีค่าเป็นบวก เรียงจากมากไปน้อย — ใช้สำหรับไฮไลต์คำเสี่ยงให้ผู้ใช้
        """
        indices = row.indices
        if self._log_ratio is None or len(indices) == 0:
            return []
        weights = row.data * self._log_ratio[indices]
        order = np.argsort(-weights)
        return [(str(self.feature_names[indices[i]]), float(weights[i])) for i in order if weights[i] > 0]

    def model_name(self) -> str:
        return f"naive_bayes_{self.language}"
