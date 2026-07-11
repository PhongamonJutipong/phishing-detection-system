"""
Smoke test สำหรับ ml/preprocess.py — โหลดโมดูลด้วย importlib โดยตรงจาก path ไฟล์
(ไม่ผ่าน `import ml.preprocess`) เพราะ ml/ ไม่ได้ตั้งใจให้เป็น installable package
เป็นแค่โฟลเดอร์สคริปต์ที่รันตรง ๆ ตามที่ README อธิบายไว้
"""
import importlib.util
import sys
from pathlib import Path

import pytest

_ML_DIR = Path(__file__).resolve().parents[1]
_REPO_ROOT = _ML_DIR.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

_spec = importlib.util.spec_from_file_location("ml_preprocess_module", _ML_DIR / "preprocess.py")
ml_preprocess = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ml_preprocess)


def test_load_raw_datasets_raises_when_no_csv(tmp_path, monkeypatch):
    monkeypatch.setattr(ml_preprocess, "RAW_DIR", tmp_path)
    with pytest.raises(FileNotFoundError):
        ml_preprocess.load_raw_datasets()


def test_load_raw_datasets_reads_valid_csv(tmp_path, monkeypatch):
    csv_path = tmp_path / "sample.csv"
    csv_path.write_text("text,label\nhello world,0\nclick here now verify account,1\n", encoding="utf-8")
    monkeypatch.setattr(ml_preprocess, "RAW_DIR", tmp_path)

    df = ml_preprocess.load_raw_datasets()
    assert len(df) == 2
    assert set(df["label"]) == {0, 1}


def test_load_raw_datasets_rejects_wrong_schema(tmp_path, monkeypatch):
    csv_path = tmp_path / "bad.csv"
    csv_path.write_text("content,is_bad\nhello,0\n", encoding="utf-8")
    monkeypatch.setattr(ml_preprocess, "RAW_DIR", tmp_path)

    with pytest.raises(ValueError):
        ml_preprocess.load_raw_datasets()
