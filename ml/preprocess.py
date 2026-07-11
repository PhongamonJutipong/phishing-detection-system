"""
เตรียมข้อมูลอีเมล (ภาษาไทย + อังกฤษ) สำหรับเทรนโมเดลจำแนกฟิชชิง
สอดคล้องกับบทที่ 3.3.2 ของเอกสารโครงงาน (การกำจัดข้อมูลขยะ, การจัดการคำหยุด, การตัดคำ)

Input : ml/data/raw/*.csv  (ต้องมีคอลัมน์ text,label  โดย label = 1 คือฟิชชิง, 0 คืออีเมลปกติ)
Output: ml/data/processed/train.csv, ml/data/processed/test.csv

หมายเหตุ: ฟังก์ชันทำความสะอาดข้อความ (clean_text) ย้ายไปอยู่ที่ common/text_cleaning.py
เพื่อให้ ml/ กับ backend/ ใช้โค้ดชุดเดียวกัน (ดูเหตุผลใน common/__init__.py)
"""
import sys
import pandas as pd
from pathlib import Path
from sklearn.model_selection import train_test_split

# เพิ่ม repo root เข้า sys.path เพื่อ import แพ็กเกจ common/ ได้ ไม่ว่าจะรันสคริปต์นี้จาก
# ที่ไหน (เช่น `python preprocess.py` ในโฟลเดอร์ ml/ หรือ `python ml/preprocess.py` จาก repo root)
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from common.text_cleaning import clean_text  # noqa: E402

RAW_DIR = Path(__file__).parent / "data" / "raw"
PROCESSED_DIR = Path(__file__).parent / "data" / "processed"


def load_raw_datasets() -> pd.DataFrame:
    csv_files = list(RAW_DIR.glob("*.csv"))
    if not csv_files:
        raise FileNotFoundError(
            f"ไม่พบไฟล์ .csv ใน {RAW_DIR} — วาง dataset (คอลัมน์ text,label) ไว้ที่นี่ก่อน"
        )
    dfs = [pd.read_csv(f) for f in csv_files]
    df = pd.concat(dfs, ignore_index=True)
    if not {"text", "label"}.issubset(df.columns):
        raise ValueError("ไฟล์ dataset ต้องมีคอลัมน์ชื่อ 'text' และ 'label' เท่านั้น")
    df = df.dropna(subset=["text", "label"]).drop_duplicates(subset=["text"])
    return df


def main():
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    df = load_raw_datasets()
    print(f"โหลดข้อมูลทั้งหมด {len(df)} แถว (phishing={df['label'].sum()}, normal={(df['label'] == 0).sum()})")

    df["clean_text"] = df["text"].apply(clean_text)
    df = df[df["clean_text"].str.len() > 0]

    train_df, test_df = train_test_split(
        df, test_size=0.20, random_state=42, stratify=df["label"]
    )  # แบ่ง 80/20 ตามบทที่ 3.3.2

    train_df.to_csv(PROCESSED_DIR / "train.csv", index=False)
    test_df.to_csv(PROCESSED_DIR / "test.csv", index=False)
    print(f"บันทึกแล้ว: train={len(train_df)} แถว, test={len(test_df)} แถว -> {PROCESSED_DIR}")


if __name__ == "__main__":
    main()
