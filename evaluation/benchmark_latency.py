"""
การทดสอบตามบทที่ 3.4.2 ข้อ 1) และ 2) — ยิงอีเมลชุดทดสอบไปที่ API ที่รันอยู่จริง แล้ววัด

  ค่าความแม่นยำ          Accuracy     = จำนวนการทำนายถูกทั้งหมด / จำนวนการทดสอบทั้งหมด      (3.1)
  ระยะเวลาประมวลผลรายครั้ง  L_i          = T_end,i - T_start,i                               (3.2)
  ค่าเฉลี่ยระยะเวลา          L_mean       = sum(L_i) / n                                    (3.3)

เกณฑ์: Accuracy >= 85% (สมมติฐาน 1.4.1) และ L_mean <= 2 วินาที (สมมติฐาน 1.4.2)
ใช้เฉพาะ standard library — ไม่ต้องติดตั้งอะไรเพิ่ม

รัน: python evaluation/benchmark_latency.py --limit 200
     (ต้องรัน ml/preprocess.py ก่อนเพื่อให้มี ml/data/processed/<lang>/test.csv)

หมายเหตุสำคัญ: ใช้ 127.0.0.1 ไม่ใช่ "localhost" — บน Windows การต่อผ่านชื่อ localhost จะลอง IPv6 (::1)
ก่อนแล้วค่อยถอยมาใช้ IPv4 ซึ่งกินเวลาคงที่ประมาณ 2 วินาทีต่อ request (วัดได้จริงบนเครื่องพัฒนา)
ทำให้ผลการวัดกลายเป็น "ไม่ผ่านเกณฑ์ 2 วินาที" ทั้งที่เวลาประมวลผลจริงของระบบอยู่ที่ระดับ 10 มิลลิวินาที
"""
import argparse
import csv
import json
import statistics
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

PROCESSED_DIR = Path(__file__).resolve().parent.parent / "ml" / "data" / "processed"
ACCURACY_TARGET = 0.85
LATENCY_TARGET_SEC = 2.0


def load_test_rows(languages: list[str], limit: int | None) -> list[dict]:
    csv.field_size_limit(10_000_000)
    rows = []
    for lang in languages:
        path = PROCESSED_DIR / lang / "test.csv"
        if not path.exists():
            print(f"[ข้าม {lang}] ไม่พบ {path}")
            continue
        with open(path, encoding="utf-8", newline="") as f:
            for row in csv.DictReader(f):
                rows.append({"text": row["text"], "label": int(row["label"]), "language": lang})
    return rows[:limit] if limit else rows


def call_api(url: str, text: str, timeout: float) -> dict:
    payload = json.dumps({"subject": "", "body_content": text}).encode("utf-8")
    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--api", default="http://127.0.0.1:8000/api/v1/analyze")
    parser.add_argument("--lang", nargs="+", default=["en", "th"])
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument("--out", default=str(Path(__file__).parent / "results" / "latency_results.csv"))
    args = parser.parse_args()

    rows = load_test_rows(args.lang, args.limit)
    if not rows:
        sys.exit("ไม่มีข้อมูลทดสอบ")

    records = []
    for i, row in enumerate(rows, start=1):
        t_start = time.perf_counter()
        try:
            result = call_api(args.api, row["text"], args.timeout)
        except (urllib.error.URLError, TimeoutError) as exc:
            sys.exit(f"เรียก API ไม่สำเร็จ ({exc}) — ตรวจสอบว่า backend รันอยู่ที่ {args.api}")
        latency = time.perf_counter() - t_start                     # (3.2)
        predicted = 1 if result["is_phishing"] else 0
        records.append({
            "no": i,
            "language": row["language"],
            "label": row["label"],
            "predicted": predicted,
            "correct": int(predicted == row["label"]),
            "risk_percentage": result["risk_percentage"],
            "latency_sec": round(latency, 6),
            "server_processing_ms": result["processing_time_ms"],
        })

    n = len(records)
    accuracy = sum(r["correct"] for r in records) / n                # (3.1)
    latencies = [r["latency_sec"] for r in records]
    mean_latency = sum(latencies) / n                                # (3.3)
    sd_latency = statistics.stdev(latencies) if n > 1 else 0.0

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(records[0]))
        writer.writeheader()
        writer.writerows(records)

    print(f"จำนวนการทดสอบ (n)          : {n}")
    for lang in args.lang:
        subset = [r for r in records if r["language"] == lang]
        if subset:
            print(f"  ค่าความแม่นยำ [{lang}]         : {sum(r['correct'] for r in subset) / len(subset):.2%}")
    print(f"ค่าความแม่นยำรวม              : {accuracy:.2%}  (เกณฑ์ >= {ACCURACY_TARGET:.0%}) "
          f"{'ผ่าน' if accuracy >= ACCURACY_TARGET else 'ไม่ผ่าน'}")
    print(f"ค่าเฉลี่ยระยะเวลา (Mean Latency) : {mean_latency:.4f} วินาที  (เกณฑ์ <= {LATENCY_TARGET_SEC} วินาที) "
          f"{'ผ่าน' if mean_latency <= LATENCY_TARGET_SEC else 'ไม่ผ่าน'}")
    print(f"ส่วนเบี่ยงเบนมาตรฐานของเวลา     : {sd_latency:.4f} วินาที")
    print(f"ระยะเวลาต่ำสุด/สูงสุด            : {min(latencies):.4f} / {max(latencies):.4f} วินาที")
    print(f"บันทึกผลรายครั้งไว้ที่ {out}")


if __name__ == "__main__":
    main()
