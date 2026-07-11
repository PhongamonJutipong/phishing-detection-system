"""
Shim บาง ๆ ที่ re-export ฟังก์ชันทำความสะอาดข้อความจาก common/text_cleaning.py

เดิมไฟล์นี้มีโค้ด copy จาก ml/preprocess.py ทั้งชุด (เสี่ยงโค้ดสองจุดไม่ตรงกัน) และอ้าง
path ของ stopwords_th.txt แบบ "../../../../ml/stopwords_th.txt" ซึ่งจะหาไฟล์ไม่เจอทันที
ถ้า deploy backend/ เป็น container แยกโดยไม่มีโฟลเดอร์ ml/ ติดไปด้วย

ตอนนี้ทั้ง ml/ และ backend/ import ฟังก์ชันจริงจาก common/text_cleaning.py ที่เดียว
(ดู common/__init__.py สำหรับเหตุผลเต็ม ๆ) — backend/Dockerfile จะ COPY common/ เข้า
image ไปด้วยเสมอ จึงไม่มีการอ้าง path ออกนอกขอบเขตที่ deploy จริง
"""
import sys
from pathlib import Path

# backend/app/ml/preprocessing.py -> parents: [0]=ml [1]=app [2]=backend [3]=repo root
_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from common.text_cleaning import (  # noqa: E402,F401
    clean_text,
    remove_noise,
    tokenize,
    remove_stopwords,
    HAS_PYTHAINLP,
)
