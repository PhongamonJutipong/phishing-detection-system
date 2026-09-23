
from common.text_cleaning import clean_text, detect_language, remove_noise, script_ratios, tokenize


def test_remove_noise_masks_url_and_email():
    # หมายเหตุ: remove_noise ลบ punctuation (รวม < >) หลังจากแทรก token <url>/<email>
    # ผลคือ token ที่เหลือจริง ๆ คือ "url"/"email" แบบไม่มีวงเล็บ — สม่ำเสมอระหว่างตอนเทรนกับใช้งานจริง
    text = remove_noise("Click http://evil.com or email me@test.com NOW!!!")
    assert "url" in text
    assert "email" in text
    assert "http://evil.com" not in text
    assert "me@test.com" not in text


def test_clean_text_removes_english_stopwords_keeps_content_words():
    tokens = clean_text("this is a test message for you").split()
    assert "this" not in tokens
    assert "is" not in tokens
    assert "test" in tokens
    assert "message" in tokens


def test_clean_text_handles_non_string_gracefully():
    assert clean_text(None) == ""
    assert clean_text(12345) == ""


def test_tokenize_splits_english_text():
    assert tokenize("hello world") == ["hello", "world"]


def test_detect_language_ignores_urls():
    assert detect_language("Please verify your account") == "en"
    assert detect_language("กรุณายืนยันตัวตนที่ http://verify-account-login.com/secure") == "th"
    ratios = script_ratios("กรุณายืนยันตัวตนที่ http://verify-account-login.com/secure")
    assert ratios["en"] == 0.0


def test_thai_custom_dictionary_keeps_phishing_terms_whole():
    import pytest

    pytest.importorskip("pythainlp")
    assert "ยืนยันตัวตน" in tokenize("กรุณายืนยันตัวตนทันที")
