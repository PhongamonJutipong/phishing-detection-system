"""
Smoke test สำหรับ ml/preprocess.py — โหลดโมดูลด้วย importlib โดยตรงจาก path ไฟล์
(ml/ ไม่ได้ตั้งใจให้เป็น installable package เป็นแค่โฟลเดอร์สคริปต์ที่รันตรง ๆ)
"""
import importlib.util
from pathlib import Path

import pytest

_ML_DIR = Path(__file__).resolve().parents[1]

_spec = importlib.util.spec_from_file_location("ml_preprocess_module", _ML_DIR / "preprocess.py")
ml_preprocess = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ml_preprocess)


def test_load_raw_datasets_raises_when_no_files(tmp_path, monkeypatch):
    monkeypatch.setattr(ml_preprocess, "RAW_DIR", tmp_path)
    with pytest.raises(FileNotFoundError):
        ml_preprocess.load_raw_datasets()


def test_load_raw_datasets_reads_csv_and_detects_language(tmp_path, monkeypatch):
    (tmp_path / "sample.csv").write_text(
        "text,label\nhello world,0\nclick here now verify account,1\nกรุณายืนยันตัวตนทันที,1\n", encoding="utf-8"
    )
    monkeypatch.setattr(ml_preprocess, "RAW_DIR", tmp_path)

    df = ml_preprocess.load_raw_datasets()
    assert len(df) == 3
    assert set(df["label"]) == {0, 1}
    assert list(df["language"]) == ["en", "en", "th"]


def test_load_raw_datasets_rejects_wrong_schema(tmp_path, monkeypatch):
    (tmp_path / "bad.csv").write_text("content,is_bad\nhello,0\n", encoding="utf-8")
    monkeypatch.setattr(ml_preprocess, "RAW_DIR", tmp_path)
    with pytest.raises(ValueError):
        ml_preprocess.load_raw_datasets()


def test_load_mock_xlsx_dataset_has_both_languages(tmp_path, monkeypatch):
    pytest.importorskip("openpyxl")
    monkeypatch.setattr(ml_preprocess, "RAW_DIR", tmp_path)
    df = ml_preprocess.load_raw_datasets(include_mock=True)
    assert {"en", "th"} <= set(df["language"])
    assert set(df["label"]) == {0, 1}
