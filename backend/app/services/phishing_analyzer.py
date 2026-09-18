"""
Class PhishingAnalyzer (แผนภาพคลาส รูปที่ 3.2, แผนภาพลำดับงาน Analyze Email รูปที่ 3.6)

ตัวกลางรับข้อมูลเจสันจากส่วนขยาย และควบคุมการทำงานของคลาสอื่นตาม UC-04:
  DatabaseManager.checkData -> NLPProcess (tokenize/removeStopWords/vectorize)
  -> PhishingModel.predict (แยกภาษาไทย/อังกฤษ แล้วเลือกค่าความเสี่ยงสูงสุด)
  -> DatabaseManager.saveSecureLog -> generateResponse (เจสัน)
"""
import re
import time

from app.config import settings
from app.core.logger import logger
from app.db.database_manager import DatabaseManager
from app.ml.model_registry import ModelRegistry
from app.nlp.nlp_process import NLPProcess
from app.schemas import EmailAnalyzeRequest, EmailAnalyzeResponse, HighlightTerm, Indicator

# รูปแบบข้อความตามทฤษฎีการโน้มน้าวใจ (บทที่ 2.1.1) ใช้อธิบายเหตุผลของความเสี่ยงให้ผู้ใช้เข้าใจ
PERSUASION_PATTERNS: dict[str, list[str]] = {
    "urgency": [
        r"ด่วนที่สุด", r"ด่วน", r"ทันที", r"ภายใน\s*\d+\s*(?:ชั่วโมง|ชม\.?|นาที|วัน)", r"ปิดถาวร", r"ระงับ",
        r"\bimmediately\b", r"\burgent(?:ly)?\b", r"\bwithin\s+\d+\s+(?:hours?|minutes?|days?)\b",
        r"\bexpir(?:e|es|ed|ing)\b", r"\bsuspend(?:ed)?\b", r"\bpermanently\b", r"\bact now\b",
    ],
    "credential_request": [
        r"รหัสผ่าน", r"ยืนยันตัวตน", r"เลขบัตร", r"บัตรเครดิต", r"\bOTP\b", r"\bCVV\b", r"ข้อมูลส่วน(?:ตัว|บุคคล)",
        r"\bpassword\b", r"\bverify (?:your )?(?:account|identity)\b", r"\bcredit card\b", r"\bPIN\b",
        r"\bsocial security\b", r"\blog ?in\b",
    ],
    "authority": [
        r"ฝ่ายไอที", r"ฝ่ายรักษาความปลอดภัย", r"ผู้บริหาร", r"ธนาคาร", r"หน่วยงานรัฐ", r"กรมสรรพากร",
        r"\bIT department\b", r"\bsecurity team\b", r"\bbank\b", r"\bgovernment\b", r"\bCEO\b", r"\badministrator\b",
    ],
    "reward": [
        r"รางวัล", r"คืนภาษี", r"โปรโมชัน", r"ฟรี", r"เงินคืน",
        r"\bwinner\b", r"\bprize\b", r"\brefund\b", r"\bfree\b", r"\bgift card\b", r"\bcongratulations\b",
    ],
    "suspicious_link": [
        r"คลิกที่นี่", r"คลิกลิงก์", r"\bclick here\b", r"\bclick (?:the )?link\b", r"\bdownload now\b",
        r"https?://[^\s\"'<>]+",
    ],
}

# token พิเศษจาก remove_noise() ที่ไม่ได้ปรากฏเป็นคำจริงในอีเมล จึงไม่นำไปไฮไลต์
_NON_HIGHLIGHT_TOKENS = {"url", "email"}


def risk_level_for(probability: float) -> str:
    """แปลงความน่าจะเป็นเป็นระดับความเสี่ยง 3 ระดับ (UC-06): แดง/เหลือง/เขียว"""
    if probability >= settings.min_risk_threshold:
        return "dangerous"
    if probability >= settings.suspicious_threshold:
        return "suspicious"
    return "safe"


class ModelUnavailableError(RuntimeError):
    """UC-04 ทางเลือก 9.1: โหลดโมเดลนาอีฟเบย์ไม่สำเร็จ"""


class PhishingAnalyzer:
    def __init__(self, registry: ModelRegistry, db_manager: DatabaseManager | None, nlp: NLPProcess | None = None):
        self.registry = registry
        self.db_manager = db_manager
        self.nlp = nlp or NLPProcess()

    def process_request(self, email: EmailAnalyzeRequest) -> EmailAnalyzeResponse:
        start = time.perf_counter()
        models = self.registry.available()
        if not models:
            raise ModelUnavailableError("ยังไม่มีโมเดลที่พร้อมใช้งาน")

        subject = email.subject or ""
        raw_text = f"{subject}\n{email.body_content}"

        # NLP: tokenize -> removeStopWords
        tokens = self.nlp.remove_stop_words(self.nlp.tokenize(raw_text))

        # เลือกโมเดลตามภาษาที่ปรากฏ แล้วคำนวณความเสี่ยงของแต่ละภาษา (UC-04 ข้อ 9)
        ratios = self.nlp.script_ratios(raw_text)
        candidates = [lang for lang in models if ratios.get(lang, 0.0) >= settings.min_language_ratio]
        if not candidates:
            dominant = "th" if ratios["th"] > ratios["en"] else "en"
            candidates = [dominant] if dominant in models else list(models)

        per_language = {}
        for lang in candidates:
            model = models[lang]
            vector = self.nlp.vectorize(tokens, model.vectorizer)
            per_language[lang] = (model, vector, model.predict(vector))
        # โมเดลที่ไม่รู้จักคำใดในอีเมลเลย (เวกเตอร์ว่าง) จะให้แค่ค่า prior ของคลาส — ไม่นำมาเทียบ
        known = {lang: v for lang, v in per_language.items() if v[1].nnz > 0}
        if known:
            per_language = known

        # เทียบค่าความเสี่ยงของแต่ละภาษาเพื่อหาค่าสูงสุด (UC-04 ข้อ 10-11)
        language = max(per_language, key=lambda lang: per_language[lang][2]["probability"])
        best_model, best_vector, best_prediction = per_language[language]
        probability = best_prediction["probability"]

        level = risk_level_for(probability)
        is_phishing = probability >= settings.min_risk_threshold
        classification = "phishing" if is_phishing else "legitimate"

        suspicious_keywords = self._keywords_for_highlight(best_prediction["suspicious_terms"])
        indicators = self._find_indicators(raw_text)
        highlights = self._build_highlights(suspicious_keywords, indicators)

        result_id = self._save_log(email, tokens, language, probability, classification, best_model, best_vector)

        elapsed_ms = (time.perf_counter() - start) * 1000
        logger.log_info(
            f"analyze: lang={language} p={probability:.4f} level={level} time={elapsed_ms:.1f}ms"
        )
        return self.generate_response({
            "result_id": result_id,
            "probability": probability,
            "risk_level": level,
            "is_phishing": is_phishing,
            "classification": classification,
            "language": language,
            "language_scores": {lang: round(v[2]["probability"], 4) for lang, v in per_language.items()},
            "highlights": highlights,
            "suspicious_keywords": [k for k, _ in suspicious_keywords],
            "indicators": indicators,
            "processing_time_ms": elapsed_ms,
        })

    @staticmethod
    def generate_response(res: dict) -> EmailAnalyzeResponse:
        """รวบรวมผลลัพธ์จากการวิเคราะห์ และจัดทำข้อมูลให้อยู่ในรูปแบบเจสัน (UC-04 ข้อ 12)"""
        return EmailAnalyzeResponse(
            result_id=res.get("result_id"),
            risk_score=round(res["probability"], 4),
            risk_percentage=round(res["probability"] * 100, 2),
            risk_level=res["risk_level"],
            is_phishing=res["is_phishing"],
            classification=res["classification"],
            language=res["language"],
            language_scores=res["language_scores"],
            highlights=[HighlightTerm(**h) for h in res["highlights"]],
            suspicious_keywords=res["suspicious_keywords"],
            indicators=[Indicator(**i) for i in res["indicators"]],
            processing_time_ms=round(res["processing_time_ms"], 2),
        )

    # ---------- helpers ----------
    @staticmethod
    def _keywords_for_highlight(terms: list[tuple[str, float]]) -> list[tuple[str, float]]:
        """แยก n-gram เป็นคำเดี่ยวเพื่อไฮไลต์ได้ในหน้าอีเมล และตัด token พิเศษออก"""
        seen: dict[str, float] = {}
        for term, weight in terms:
            for word in term.split():
                if word in _NON_HIGHLIGHT_TOKENS or len(word) < 2:
                    continue
                seen[word] = max(seen.get(word, 0.0), weight)
        ranked = sorted(seen.items(), key=lambda kv: -kv[1])
        return ranked[: settings.max_highlight_terms]

    @staticmethod
    def _find_indicators(raw_text: str) -> list[dict]:
        indicators = []
        for category, patterns in PERSUASION_PATTERNS.items():
            phrases: list[str] = []
            for pattern in patterns:
                for match in re.finditer(pattern, raw_text, flags=re.IGNORECASE):
                    phrase = match.group(0).strip()
                    if phrase and phrase.lower() not in (p.lower() for p in phrases):
                        phrases.append(phrase)
            if phrases:
                indicators.append({"category": category, "phrases": phrases[:10]})
        return indicators

    @staticmethod
    def _build_highlights(keywords, indicators) -> list[dict]:
        highlights = [{"phrase": word, "reason": "model_keyword", "weight": round(w, 4)} for word, w in keywords]
        for indicator in indicators:
            for phrase in indicator["phrases"]:
                highlights.append({"phrase": phrase, "reason": indicator["category"], "weight": 0.0})
        return highlights

    def _save_log(self, email, tokens, language, probability, classification, model, vector):
        """บันทึกประวัติการสแกน — ถ้าฐานข้อมูลมีปัญหา ยังคืนผลวิเคราะห์ให้ผู้ใช้ได้ (บันทึก error ไว้)"""
        if self.db_manager is None:
            return None
        try:
            counts = self.nlp.word_frequency(tokens)
            total = max(len(tokens), 1)
            vocab = model.vectorizer.vocabulary_
            idf = getattr(model.vectorizer, "idf_", None)
            row = vector.tocsr()

            tfidf_rows = []
            for word, freq in counts.items():
                idx = vocab.get(word)
                if idx is None:
                    continue
                tfidf_rows.append((
                    word, freq / total, float(idf[idx]) if idf is not None else None, float(row[0, idx])
                ))
            names = model.vectorizer.get_feature_names_out()
            features = [(str(names[i]), float(v)) for i, v in zip(row.indices, row.data)]

            result = self.db_manager.save_secure_log({
                "subject": email.subject or "",
                "body": email.body_content,
                "body_hash": DatabaseManager.make_body_hash(email.subject or "", email.body_content),
                "language": language,
                "probability": probability,
                "classification": classification,
                "model": model,
                "token_counts": counts,
                "tfidf_rows": tfidf_rows,
                "features": features,
            })
            return str(result.result_id)
        except Exception as exc:
            logger.log_error(f"บันทึกผลการสแกนลงฐานข้อมูลไม่สำเร็จ: {exc}")
            return None
