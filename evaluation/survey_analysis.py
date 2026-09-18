"""
วิเคราะห์ผลแบบประเมินการยอมรับเทคโนโลยี (บทที่ 3.4.2 ข้อ 3) จากไฟล์ CSV ที่ export จาก Google Forms

สถิติที่ใช้ (บทที่ 3.4.1):
  ค่าเฉลี่ย             x̄ = Σx / n                               (3.4)
  ส่วนเบี่ยงเบนมาตรฐาน    S.D. = sqrt( Σ(x - x̄)² / (n - 1) )        (3.5)
  ร้อยละ               P = f / n x 100                           (3.6)
  ความกว้างอันตรภาคชั้น   I = (ค่าสูงสุด - ค่าต่ำสุด) / จำนวนระดับ      (3.7) = (5 - 1) / 5 = 0.80

รูปแบบไฟล์: แต่ละแถว = ผู้ประเมิน 1 คน, คอลัมน์คำถามตั้งชื่อเป็น "<ด้าน>: <ข้อคำถาม>"
  เช่น "ด้านฟังก์ชันการทำงาน: ระบบแสดงระดับความเสี่ยงได้ชัดเจน" ค่าเป็นคะแนน 1-5
  คอลัมน์อื่น (เช่น Timestamp, สถานะ) ที่ไม่ใช่ตัวเลข 1-5 จะถูกใช้เป็นข้อมูลทั่วไปสำหรับคำนวณร้อยละ

รัน: python evaluation/survey_analysis.py responses.csv [--group-column "สถานะ"]
"""
import argparse
import csv
import math
from collections import Counter, OrderedDict

SCALE_MIN, SCALE_MAX, LEVELS = 1, 5, 5
INTERVAL = (SCALE_MAX - SCALE_MIN) / LEVELS   # (3.7)

# ตารางที่ 3.15 เกณฑ์การแปลผลคะแนนการประเมินคุณภาพของระบบ
INTERPRETATION = [
    (4.21, "มากที่สุด"),
    (3.41, "มาก"),
    (2.61, "ปานกลาง"),
    (1.81, "น้อย"),
    (1.00, "น้อยที่สุด"),
]


def interpret(mean: float) -> str:
    for lower, label in INTERPRETATION:
        if mean >= lower:
            return label
    return INTERPRETATION[-1][1]


def mean_sd(values: list[float]) -> tuple[float, float]:
    n = len(values)
    mean = sum(values) / n                                                   # (3.4)
    sd = math.sqrt(sum((x - mean) ** 2 for x in values) / (n - 1)) if n > 1 else 0.0   # (3.5)
    return mean, sd


def _score(value: str) -> int | None:
    try:
        number = int(float(value.strip()))
    except (ValueError, AttributeError):
        return None
    return number if SCALE_MIN <= number <= SCALE_MAX else None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("csv_file")
    parser.add_argument("--group-column", help="คอลัมน์ข้อมูลทั่วไปที่ต้องการคำนวณร้อยละ เช่น สถานะผู้ประเมิน")
    args = parser.parse_args()

    with open(args.csv_file, encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        raise SystemExit("ไฟล์ไม่มีข้อมูล")

    n = len(rows)
    question_columns = [
        c for c in rows[0] if ":" in c and all(_score(r[c]) is not None for r in rows if r[c].strip())
    ]
    if not question_columns:
        raise SystemExit('ไม่พบคอลัมน์คำถามรูปแบบ "<ด้าน>: <ข้อคำถาม>" ที่มีคะแนน 1-5')

    print(f"จำนวนผู้ประเมิน n = {n}   ความกว้างอันตรภาคชั้น = {INTERVAL:.2f}\n")

    if args.group_column:
        print(f"ข้อมูลทั่วไป: {args.group_column}")
        for value, freq in Counter(r[args.group_column] for r in rows).most_common():
            print(f"  {value:30s} {freq:4d}  ร้อยละ {freq / n * 100:.2f}")   # (3.6)
        print()

    aspects: "OrderedDict[str, list[str]]" = OrderedDict()
    for column in question_columns:
        aspects.setdefault(column.split(":", 1)[0].strip(), []).append(column)

    all_scores: list[int] = []
    print(f"{'รายการประเมิน':70s} {'x̄':>5s} {'S.D.':>5s}  ระดับ")
    for aspect, columns in aspects.items():
        aspect_scores: list[int] = []
        print(f"\n{aspect}")
        for column in columns:
            scores = [s for s in (_score(r[column]) for r in rows) if s is not None]
            aspect_scores.extend(scores)
            m, sd = mean_sd(scores)
            print(f"  {column.split(':', 1)[1].strip()[:66]:68s} {m:5.2f} {sd:5.2f}  {interpret(m)}")
        m, sd = mean_sd(aspect_scores)
        print(f"  {'รวม' + aspect:68s} {m:5.2f} {sd:5.2f}  {interpret(m)}")
        all_scores.extend(aspect_scores)

    m, sd = mean_sd(all_scores)
    print(f"\n{'ภาพรวมทุกด้าน':70s} {m:5.2f} {sd:5.2f}  {interpret(m)}")


if __name__ == "__main__":
    main()
