"""
Class Logger (แผนภาพคลาส รูปที่ 3.2)

บันทึกเหตุการณ์ของระบบหลังบ้านลงไฟล์ (logFile) และ console ตามระดับ (logLevel)
"""
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from app.config import settings


class Logger:
    def __init__(self, log_file: str | None = None, log_level: str | None = None, name: str = "phishing"):
        self.log_file = log_file or settings.log_file
        self.log_level = (log_level or settings.log_level).upper()

        self._logger = logging.getLogger(name)
        self._logger.setLevel(self.log_level)
        if not self._logger.handlers:
            fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
            console = logging.StreamHandler()
            console.setFormatter(fmt)
            self._logger.addHandler(console)
            try:
                Path(self.log_file).parent.mkdir(parents=True, exist_ok=True)
                file_handler = RotatingFileHandler(
                    self.log_file, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"
                )
                file_handler.setFormatter(fmt)
                self._logger.addHandler(file_handler)
            except OSError:
                # เขียนไฟล์ไม่ได้ (เช่น read-only filesystem) ยังบันทึกผ่าน console ได้
                self._logger.warning("ไม่สามารถเปิดไฟล์ log %s ได้ — บันทึกเฉพาะ console", self.log_file)

    def log_error(self, msg: str) -> None:
        """บันทึกรายละเอียดข้อผิดพลาดในระบบหลังบ้าน"""
        self._logger.error(msg)

    def log_info(self, msg: str) -> None:
        """บันทึกสถานการณ์ทำงานปกติของระบบหลังบ้าน"""
        self._logger.info(msg)

    def log_warning(self, msg: str) -> None:
        self._logger.warning(msg)


logger = Logger()
