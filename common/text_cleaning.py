# -*- coding: utf-8 -*-
"""
ฟังก์ชันทำความสะอาดข้อความ (text preprocessing) — single source of truth

ใช้ร่วมกันโดย:
  - ml/preprocess.py      (ตอนเตรียมข้อมูลเทรนโมเดล)
  - backend/app/ml/preprocessing.py (ตอนรับ request จริงจาก extension)

ทั้งสองที่ต้องประมวลผลข้อความ "เหมือนกันทุกตัวอักษร" ไม่เช่นนั้นโมเดลจะทำนายผิดเพี้ยน
(อธิบายไว้ใน README) — เดิมเคย copy โค้ดชุดนี้ไว้ 2 จุดแยกกัน จึงย้ายมารวมไว้ที่นี่ที่เดียว
"""
import re
import string
from pathlib import Path
from functools import lru_cache

DEFAULT_STOPWORDS_TH_PATH = Path(__file__).parent / "resources" / "stopwords_th.txt"

ENGLISH_STOPWORDS = {
    "the", "is", "at", "a", "an", "and", "or", "to", "of", "in", "on",
    "for", "with", "this", "that", "it", "as", "be", "by", "are", "was",
    "were", "will", "your", "you", "we", "our", "i", "from", "has", "have",
}

try:
    from pythainlp.tokenize import word_tokenize as _th_tokenize
    from pythainlp.util import isthai as _isthai
    HAS_PYTHAINLP = True
except ImportError:
    HAS_PYTHAINLP = False


@lru_cache(maxsize=4)
def load_thai_stopwords(path: str | None = None) -> frozenset:
    """โหลด stopwords ภาษาไทยจากไฟล์ (cache ไว้เพราะอ่านไฟล์ทุกครั้งไม่จำเป็น)"""
    p = Path(path) if path else DEFAULT_STOPWORDS_TH_PATH
    if p.exists():
        return frozenset(w.strip() for w in p.read_text(encoding="utf-8").splitlines() if w.strip())
    return frozenset()


def remove_noise(text: str) -> str:
    """ลบอักขระพิเศษ, แทนที่ URL/อีเมลด้วย token พิเศษ, ช่องว่างซ้ำ"""
    text = text.lower()
    text = re.sub(r"http\S+|www\.\S+", " <url> ", text)
    text = re.sub(r"\S+@\S+", " <email> ", text)
    text = text.translate(str.maketrans("", "", string.punctuation))
    text = re.sub(r"\s+", " ", text).strip()
    return text


def tokenize(text: str) -> list[str]:
    """ตัดคำแบบผสมภาษา: ใช้ pythainlp สำหรับส่วนที่เป็นไทย, split() สำหรับอังกฤษ"""
    if HAS_PYTHAINLP and any(_isthai(ch) for ch in text):
        tokens = _th_tokenize(text, engine="newmm")
    else:
        tokens = text.split()
    return [t.strip() for t in tokens if t.strip()]


def remove_stopwords(tokens: list[str], stopwords_path: str | None = None) -> list[str]:
    thai_stopwords = load_thai_stopwords(stopwords_path)
    return [t for t in tokens if t not in thai_stopwords and t not in ENGLISH_STOPWORDS]


def clean_text(text: str, stopwords_path: str | None = None) -> str:
    """pipeline เต็ม: noise removal -> tokenize -> remove stopwords -> join กลับเป็น string สำหรับ TF-IDF"""
    if not isinstance(text, str):
        return ""
    text = remove_noise(text)
    tokens = tokenize(text)
    tokens = remove_stopwords(tokens, stopwords_path)
    return " ".join(tokens)
