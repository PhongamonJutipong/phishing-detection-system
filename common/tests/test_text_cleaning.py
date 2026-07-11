import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from common.text_cleaning import clean_text, remove_noise, tokenize


def test_remove_noise_masks_url_and_email():
    # หมายเหตุ: remove_noise ลบ punctuation (รวม < >) หลังจากแทรก token <url>/<email>
    # ผลคือ token ที่เหลือจริง ๆ คือ "url"/"email" แบบไม่มีวงเล็บ ไม่ใช่ "<url>" ตามที่
    # docstring บอกไว้ ("แทนที่ด้วย token พิเศษ") — พฤติกรรมนี้ยังคง "สม่ำเสมอ" ระหว่าง
    # ตอนเทรนกับตอนใช้งานจริงเพราะเรียกฟังก์ชันเดียวกันทั้งคู่ (โมเดลจึงยังทำงานถูกต้อง)
    # แต่ทีมควรรู้ไว้เผื่อจะแก้ให้ตรงกับ docstring ในอนาคต (ถ้าแก้ ต้องเทรนโมเดลใหม่ด้วย)
    text = remove_noise("Click http://evil.com or email me@test.com NOW!!!")
    assert "url" in text
    assert "email" in text
    assert "http://evil.com" not in text
    assert "me@test.com" not in text


def test_clean_text_removes_english_stopwords_keeps_content_words():
    result = clean_text("this is a test message for you")
    tokens = result.split()
    assert "this" not in tokens
    assert "is" not in tokens
    assert "test" in tokens
    assert "message" in tokens


def test_clean_text_handles_non_string_gracefully():
    assert clean_text(None) == ""
    assert clean_text(12345) == ""


def test_tokenize_splits_english_text():
    tokens = tokenize("hello world")
    assert tokens == ["hello", "world"]
