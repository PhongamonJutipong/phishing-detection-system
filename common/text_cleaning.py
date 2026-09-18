# -*- coding: utf-8 -*-
"""
ฟังก์ชันทำความสะอาดข้อความ (text preprocessing) — single source of truth

ใช้ร่วมกันโดย:
  - ml/preprocess.py, ml/train.py        (ตอนเตรียมข้อมูล/เทรนโมเดล)
  - backend/app/nlp/nlp_process.py       (ตอนรับ request จริงจาก extension)

ทั้งสองที่ต้องประมวลผลข้อความ "เหมือนกันทุกตัวอักษร" ไม่เช่นนั้นโมเดลจะทำนายผิดเพี้ยน
ขั้นตอนตามบทที่ 3.3.2: กำจัดข้อมูลขยะ -> ตัดคำ (ใช้คลังคำศัพท์) -> จัดการคำหยุด
"""
import re
import string
from pathlib import Path
from functools import lru_cache

RESOURCES_DIR = Path(__file__).parent / "resources"
DEFAULT_STOPWORDS_TH_PATH = RESOURCES_DIR / "stopwords_th.txt"
# คลังคำศัพท์เสริมสำหรับตัดคำภาษาไทย (dictionaryPath ใน Class NLPProcess)
DEFAULT_DICTIONARY_TH_PATH = RESOURCES_DIR / "custom_dict_th.txt"

SUPPORTED_LANGUAGES = ("en", "th")

ENGLISH_STOPWORDS = {
    "the", "is", "at", "a", "an", "and", "or", "to", "of", "in", "on",
    "for", "with", "this", "that", "it", "as", "be", "by", "are", "was",
    "were", "will", "your", "you", "we", "our", "i", "from", "has", "have",
}

_THAI_CHAR_RE = re.compile(r"[฀-๿]")
_LATIN_CHAR_RE = re.compile(r"[A-Za-z]")

try:
    from pythainlp.tokenize import word_tokenize as _th_tokenize
    from pythainlp.corpus.common import thai_words as _thai_words
    from pythainlp.util import dict_trie as _dict_trie
    HAS_PYTHAINLP = True
except ImportError:
    HAS_PYTHAINLP = False


def _read_word_file(path: Path) -> frozenset:
    if path.exists():
        return frozenset(w.strip() for w in path.read_text(encoding="utf-8").splitlines() if w.strip())
    return frozenset()


@lru_cache(maxsize=4)
def load_thai_stopwords(path: str | None = None) -> frozenset:
    """โหลด stopwords ภาษาไทยจากไฟล์ (cache ไว้เพราะอ่านไฟล์ทุกครั้งไม่จำเป็น)"""
    return _read_word_file(Path(path) if path else DEFAULT_STOPWORDS_TH_PATH)


@lru_cache(maxsize=4)
def load_thai_dictionary(path: str | None = None):
    """สร้าง Trie ของคลังคำศัพท์ (คำมาตรฐานของ pythainlp + คำเฉพาะด้านฟิชชิง) สำหรับตัดคำ"""
    if not HAS_PYTHAINLP:
        return None
    custom = _read_word_file(Path(path) if path else DEFAULT_DICTIONARY_TH_PATH)
    return _dict_trie(set(_thai_words()) | set(custom))


def script_ratios(text: str) -> dict[str, float]:
    """สัดส่วนตัวอักษรไทย/อังกฤษในข้อความ (ใช้ตัดสินว่าจะส่งให้โมเดลภาษาใดวิเคราะห์)"""
    if not isinstance(text, str):
        return {"th": 0.0, "en": 0.0}
    # ไม่นับ URL/ที่อยู่อีเมล เพราะเป็นอักษรละตินเสมอแม้เนื้อหาจะเป็นภาษาไทย
    text = re.sub(r"http\S+|www\.\S+|\S+@\S+", " ", text)
    th = len(_THAI_CHAR_RE.findall(text))
    en = len(_LATIN_CHAR_RE.findall(text))
    total = th + en
    if total == 0:
        return {"th": 0.0, "en": 0.0}
    return {"th": th / total, "en": en / total}


def detect_language(text: str) -> str:
    """ภาษาหลักของข้อความ: 'th' ถ้าตัวอักษรไทยมากกว่า ไม่เช่นนั้น 'en'"""
    ratios = script_ratios(text)
    return "th" if ratios["th"] > ratios["en"] else "en"


def remove_noise(text: str) -> str:
    """ลบอักขระพิเศษ, แทนที่ URL/อีเมลด้วย token พิเศษ, ช่องว่างซ้ำ"""
    text = text.lower()
    text = re.sub(r"http\S+|www\.\S+", " <url> ", text)
    text = re.sub(r"\S+@\S+", " <email> ", text)
    text = text.translate(str.maketrans("", "", string.punctuation))
    text = re.sub(r"\s+", " ", text).strip()
    return text


def tokenize(text: str, dictionary_path: str | None = None) -> list[str]:
    """ตัดคำแบบผสมภาษา: ใช้ pythainlp + คลังคำศัพท์สำหรับส่วนที่เป็นไทย, split() สำหรับอังกฤษ"""
    if HAS_PYTHAINLP and _THAI_CHAR_RE.search(text):
        tokens = _th_tokenize(text, custom_dict=load_thai_dictionary(dictionary_path), engine="newmm")
    else:
        tokens = text.split()
    return [t.strip() for t in tokens if t.strip()]


def remove_stopwords(tokens: list[str], stopwords_path: str | None = None) -> list[str]:
    thai_stopwords = load_thai_stopwords(stopwords_path)
    return [t for t in tokens if t not in thai_stopwords and t not in ENGLISH_STOPWORDS]


def clean_tokens(
    text: str, stopwords_path: str | None = None, dictionary_path: str | None = None
) -> list[str]:
    """noise removal -> tokenize -> remove stopwords (คืนค่าเป็นรายการคำ)"""
    if not isinstance(text, str):
        return []
    return remove_stopwords(tokenize(remove_noise(text), dictionary_path), stopwords_path)


def clean_text(
    text: str, stopwords_path: str | None = None, dictionary_path: str | None = None
) -> str:
    """pipeline เต็ม แล้ว join กลับเป็น string สำหรับ TF-IDF"""
    return " ".join(clean_tokens(text, stopwords_path, dictionary_path))
