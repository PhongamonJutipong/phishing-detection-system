"""
Class NLPProcess (แผนภาพคลาส รูปที่ 3.2)

ขั้นตอนการประมวลผลภาษาธรรมชาติ: tokenize() -> removeStopWords() -> vectorize()
ใช้ฟังก์ชันจาก common/text_cleaning.py ชุดเดียวกับตอนเทรนโมเดล
"""
import sys
from collections import Counter
from pathlib import Path

# backend/app/nlp/nlp_process.py -> parents[3] = repo root (ตอน dev) ; ใน Docker common/ อยู่ที่ /app
_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from common import text_cleaning  # noqa: E402


class NLPProcess:
    def __init__(self, stopwords_path: str | None = None, dictionary_path: str | None = None):
        self.dictionary_path = dictionary_path
        self.stopword_list = text_cleaning.load_thai_stopwords(stopwords_path) | frozenset(
            text_cleaning.ENGLISH_STOPWORDS
        )
        self._stopwords_path = stopwords_path

    def tokenize(self, text: str) -> list[str]:
        """ตัดข้อความเนื้อหาอีเมล (หลังกำจัดข้อมูลขยะ) เป็นช่วงคำ"""
        if not isinstance(text, str):
            return []
        return text_cleaning.tokenize(text_cleaning.remove_noise(text), self.dictionary_path)

    def remove_stop_words(self, words: list[str]) -> list[str]:
        """ลบคำที่ไม่มีผลต่อการวิเคราะห์"""
        return text_cleaning.remove_stopwords(words, self._stopwords_path)

    @staticmethod
    def vectorize(words: list[str], vectorizer):
        """แปลงรายการคำศัพท์เป็นเวกเตอร์ TF-IDF ด้วย vectorizer ที่เทรนไว้ของแต่ละภาษา"""
        return vectorizer.transform([" ".join(words)])

    @staticmethod
    def word_frequency(words: list[str]) -> Counter:
        return Counter(words)

    @staticmethod
    def script_ratios(text: str) -> dict[str, float]:
        return text_cleaning.script_ratios(text)
