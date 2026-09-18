"""
ทะเบียนโมเดลของแต่ละภาษา (en / th) — โหลดครั้งเดียวตอนเริ่มระบบ และโหลดใหม่ได้เมื่อมีโมเดลรุ่นใหม่
(รองรับการอัปเดตโมเดลอัตโนมัติ ตามบทที่ 3.1.5)
"""
import threading
from pathlib import Path

from app.config import settings
from app.core.logger import logger
from app.ml.phishing_model import PhishingModel

LANGUAGES = ("en", "th")


class ModelRegistry:
    def __init__(self, model_dir: str | None = None):
        self.model_dir = Path(model_dir or settings.model_dir)
        self.models: dict[str, PhishingModel] = {}
        self._lock = threading.Lock()

    def load_all(self) -> dict[str, PhishingModel]:
        loaded: dict[str, PhishingModel] = {}
        for lang in LANGUAGES:
            model = PhishingModel(self.model_dir / lang, lang)
            try:
                model.load_model()
                loaded[lang] = model
                logger.log_info(f"โหลดโมเดลภาษา {lang} สำเร็จ ({model.model_path})")
            except FileNotFoundError as exc:
                logger.log_warning(str(exc))
            except Exception as exc:  # ไฟล์เสีย / sklearn คนละเวอร์ชัน
                logger.log_error(f"โหลดโมเดลภาษา {lang} ไม่สำเร็จ: {exc}")
        with self._lock:
            self.models = loaded
        return loaded

    def available(self) -> dict[str, PhishingModel]:
        with self._lock:
            return dict(self.models)


_registry: ModelRegistry | None = None


def get_model_registry() -> ModelRegistry:
    global _registry
    if _registry is None:
        _registry = ModelRegistry()
        _registry.load_all()
    return _registry
