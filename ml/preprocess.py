"""
เตรียมข้อมูลอีเมล (ภาษาไทย + อังกฤษ) สำหรับเทรนโมเดลจำแนกฟิชชิง — บทที่ 3.3.2

1) การทำความเข้าใจข้อมูล: รวบรวมข้อมูล, ตรวจค่าที่ขาดหาย/ข้อมูลซ้ำ, การกระจายจำนวนคำ, คำที่พบบ่อยในฟิชชิง
2) การจัดเตรียมข้อมูล: กำจัดข้อมูลขยะ -> ตัดคำ -> จัดการคำหยุด -> แบ่งข้อมูล 80/20 (แยกตามภาษา)

Input : ml/data/raw/*.csv   คอลัมน์ text,label[,language]   (label 1 = ฟิชชิง, 0 = อีเมลปกติ)
        ml/data/raw/*.xlsx  ชีตที่มีคอลัมน์ข้อความ + Label (เช่น ml/data/mock_email_dataset.xlsx)
Output: ml/data/processed/{en,th}/train.csv, test.csv

รัน: python preprocess.py [--include-mock]
"""
import argparse
import sys
from collections import Counter
from pathlib import Path

import pandas as pd
from sklearn.model_selection import train_test_split

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from common.text_cleaning import SUPPORTED_LANGUAGES, clean_text, detect_language  # noqa: E402

DATA_DIR = Path(__file__).parent / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
MOCK_DATASET = DATA_DIR / "mock_email_dataset.xlsx"

TEST_SIZE = 0.20
RANDOM_STATE = 42

_TEXT_COLUMN_CANDIDATES = ("text", "text (email content)", "body", "content")
_LABEL_COLUMN_CANDIDATES = ("label", "is_phishing")


def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame | None:
    """หาคอลัมน์ข้อความ/ป้ายกำกับจากชื่อที่พบบ่อย แล้วเปลี่ยนชื่อเป็น text,label"""
    lower = {c.lower().strip(): c for c in df.columns}
    text_col = next((lower[c] for c in _TEXT_COLUMN_CANDIDATES if c in lower), None)
    label_col = next((lower[c] for c in _LABEL_COLUMN_CANDIDATES if c in lower), None)
    if text_col is None or label_col is None:
        return None
    out = df.rename(columns={text_col: "text", label_col: "label"})
    keep = ["text", "label"] + (["language"] if "language" in lower else [])
    if "language" in lower:
        out = out.rename(columns={lower["language"]: "language"})
    return out[keep]


def _read_file(path: Path) -> list[pd.DataFrame]:
    if path.suffix.lower() == ".csv":
        frames = [pd.read_csv(path)]
    else:
        frames = list(pd.read_excel(path, sheet_name=None).values())
    result = []
    for frame in frames:
        normalized = _normalize_columns(frame)
        if normalized is not None:
            result.append(normalized)
    return result


def load_raw_datasets(include_mock: bool = False) -> pd.DataFrame:
    files = sorted(list(RAW_DIR.glob("*.csv")) + list(RAW_DIR.glob("*.xlsx")))
    if include_mock and MOCK_DATASET.exists():
        files.append(MOCK_DATASET)
    if not files:
        raise FileNotFoundError(
            f"ไม่พบไฟล์ .csv/.xlsx ใน {RAW_DIR} — วาง dataset (คอลัมน์ text,label) ไว้ที่นี่ "
            "หรือรันด้วย --include-mock เพื่อใช้ชุดข้อมูลจำลอง"
        )

    frames = [frame for f in files for frame in _read_file(f)]
    if not frames:
        raise ValueError("ไฟล์ dataset ต้องมีคอลัมน์ข้อความ ('text') และป้ายกำกับ ('label')")

    df = pd.concat(frames, ignore_index=True)
    before = len(df)
    df = df.dropna(subset=["text", "label"])
    missing = before - len(df)
    df["text"] = df["text"].astype(str)
    df["label"] = df["label"].astype(int)
    before = len(df)
    df = df.drop_duplicates(subset=["text"])
    duplicates = before - len(df)

    if "language" not in df.columns:
        df["language"] = None
    df["language"] = [
        lang if lang in SUPPORTED_LANGUAGES else detect_language(text)
        for text, lang in zip(df["text"], df["language"])
    ]
    print(f"ตรวจสอบความผิดปกติ: ค่าที่ขาดหาย {missing} แถว, ข้อมูลซ้ำ {duplicates} แถว (ลบออกแล้ว)")
    return df


def explore(df: pd.DataFrame) -> None:
    """การวิเคราะห์เชิงสำรวจ: สัดส่วนป้ายกำกับ, การกระจายจำนวนคำ, คำที่พบบ่อยในอีเมลฟิชชิง"""
    for lang, group in df.groupby("language"):
        phishing = int(group["label"].sum())
        normal = int((group["label"] == 0).sum())
        total = len(group)
        print(f"\n[{lang}] ทั้งหมด {total} ฉบับ | ปกติ {normal} ({normal / total:.0%}) | ฟิชชิง {phishing} ({phishing / total:.0%})")
        words = group["clean_text"].str.split().str.len()
        print(group.assign(words=words).groupby("label")["words"].describe()[["mean", "50%", "max"]]
              .rename(index={0: "ปกติ", 1: "ฟิชชิง"}).to_string())
        top = Counter(w for t in group.loc[group["label"] == 1, "clean_text"] for w in t.split()).most_common(15)
        print("คำที่พบบ่อยในฟิชชิง:", ", ".join(f"{w}({c})" for w, c in top))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--include-mock", action="store_true", help="รวม ml/data/mock_email_dataset.xlsx ด้วย")
    args = parser.parse_args()

    df = load_raw_datasets(include_mock=args.include_mock)
    df["clean_text"] = df["text"].apply(clean_text)
    df = df[df["clean_text"].str.len() > 0]
    explore(df)

    for lang, group in df.groupby("language"):
        if group["label"].nunique() < 2:
            print(f"\n[ข้าม {lang}] ต้องมีทั้งอีเมลปกติและฟิชชิง")
            continue
        stratify = group["label"] if group["label"].value_counts().min() >= 2 else None
        train_df, test_df = train_test_split(
            group, test_size=TEST_SIZE, random_state=RANDOM_STATE, stratify=stratify
        )  # แบ่ง 80/20 ตามบทที่ 3.3.2
        out_dir = PROCESSED_DIR / lang
        out_dir.mkdir(parents=True, exist_ok=True)
        train_df.to_csv(out_dir / "train.csv", index=False)
        test_df.to_csv(out_dir / "test.csv", index=False)
        print(f"\n[{lang}] บันทึกแล้ว: train={len(train_df)} test={len(test_df)} -> {out_dir}")


if __name__ == "__main__":
    main()
