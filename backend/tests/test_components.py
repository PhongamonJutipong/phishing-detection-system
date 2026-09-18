"""
Unit test ของคลาสตามแผนภาพคลาส: NLPProcess, PhishingModel, DatabaseManager, PhishingAnalyzer
"""
from cryptography.fernet import Fernet

from app.config import get_config, settings
from app.db.database import SessionLocal
from app.db.database_manager import DatabaseManager
from app.nlp.nlp_process import NLPProcess
from app.services.phishing_analyzer import PhishingAnalyzer, risk_level_for


def test_get_config_accepts_class_diagram_key_names():
    assert get_config("MIN_RISK_THRESHOLD") == settings.min_risk_threshold
    assert get_config("does_not_exist", "fallback") == "fallback"


def test_risk_level_has_three_levels():
    assert risk_level_for(0.95) == "dangerous"
    assert risk_level_for(settings.min_risk_threshold) == "dangerous"
    assert risk_level_for(settings.suspicious_threshold) == "suspicious"
    assert risk_level_for(0.0) == "safe"


def test_nlp_process_pipeline():
    nlp = NLPProcess()
    tokens = nlp.tokenize("Please VERIFY your account at http://evil.com")
    assert "verify" in tokens
    words = nlp.remove_stop_words(tokens)
    assert "your" not in words
    assert "account" in words


def test_phishing_model_returns_probability_and_terms(registry):
    model = registry.available()["en"]
    nlp = NLPProcess()
    vector = nlp.vectorize(nlp.remove_stop_words(nlp.tokenize("verify your password immediately")), model.vectorizer)
    prediction = model.predict(vector)
    assert 0.0 <= prediction["probability"] <= 1.0
    terms = [t for t, _ in prediction["suspicious_terms"]]
    assert "verify" in terms or "password" in terms


def test_database_manager_encrypt_roundtrip():
    key = Fernet.generate_key().decode()
    with SessionLocal() as db:
        manager = DatabaseManager(db, encryption_key=key)
        token = manager.encrypt("ข้อมูลลับ secret")
        assert token != "ข้อมูลลับ secret"
        assert manager.decrypt(token) == "ข้อมูลลับ secret"
        assert DatabaseManager(db, encryption_key=Fernet.generate_key().decode()).decrypt(token) is None


def test_analyzer_highlights_skip_special_tokens():
    keywords = PhishingAnalyzer._keywords_for_highlight([("click url", 2.0), ("verify", 1.5), ("url", 1.0)])
    words = [w for w, _ in keywords]
    assert "url" not in words
    assert words[:2] == ["click", "verify"]
