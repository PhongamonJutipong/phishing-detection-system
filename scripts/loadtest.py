"""
ทดสอบภาระของ backend: ยิง POST /api/v1/analyze พร้อมกันหลายคำขอ แล้ววัดจำนวนคำขอต่อวินาทีและเวลาตอบกลับ

รัน:  python scripts/loadtest.py --url http://localhost:8000 --concurrency 1 10 50 --duration 15

ข้อควรระวัง
- ทุกคำขอถูกบันทึกลงฐานข้อมูลจริง ให้ยิงใส่ฐานข้อมูลทดสอบ ไม่ใช่ฐานข้อมูลที่ใช้งาน
  ไม่อย่างนั้นหน้าภาพรวมจะเต็มไปด้วยผลจาก load test
- ต้องปิด rate limit ของ instance ที่ทดสอบ (ANALYZE_RATE_LIMIT_PER_MINUTE=0)
  ไม่อย่างนั้นคำขอจากเครื่องเดียวจะโดนตอบ 429 เกือบทั้งหมด
- เนื้อหาอีเมลสุ่มต่อท้ายทุกคำขอ เพื่อไม่ให้ทุกคำขอเข้าทางลัด "เคยเห็นอีเมลนี้แล้ว"
"""
import argparse
import asyncio
import json
import random
import statistics
import time

import httpx

SAMPLES = [
    ("Security alert", "Urgent: your account has been suspended. Please verify your identity and confirm "
                       "your password at http://secure-login.com within 24 hours or it will be closed."),
    ("Meeting notes", "Hi team, attaching the minutes from today's meeting. The project report is due on "
                      "Friday, please upload it to the shared folder. See you next week."),
    ("แจ้งเตือนด่วน", "บัญชีของท่านถูกระงับชั่วคราว กรุณายืนยันตัวตนและกรอกรหัส OTP ที่ "
                      "http://verify-bank.info ภายใน 24 ชั่วโมง มิฉะนั้นบัญชีจะถูกปิดถาวร"),
    ("ประชุมทีม", "สวัสดีครับทีมงาน ขอเลื่อนประชุมประจำสัปดาห์เป็นวันพฤหัสบดี เวลา 10 โมง "
                  "ที่ห้องประชุมชั้น 3 รบกวนเตรียมรายงานความคืบหน้ามาด้วยครับ"),
]


def make_payload() -> bytes:
    subject, body = random.choice(SAMPLES)
    body = f"{body} ref {random.getrandbits(48):x}"
    # ส่งเป็น UTF-8 เอง ไม่พึ่งการเข้ารหัสของ shell (ภาษาไทยจะเพี้ยนถ้ายิงผ่าน curl)
    return json.dumps({"subject": subject, "body_content": body}, ensure_ascii=False).encode("utf-8")


async def worker(client: httpx.AsyncClient, url: str, stop_at: float, latencies: list, errors: dict, headers: dict):
    while time.perf_counter() < stop_at:
        start = time.perf_counter()
        try:
            resp = await client.post(url, content=make_payload(), headers=headers)
            if resp.status_code == 200:
                latencies.append((time.perf_counter() - start) * 1000)
            else:
                errors[resp.status_code] = errors.get(resp.status_code, 0) + 1
        except httpx.HTTPError as exc:
            errors[type(exc).__name__] = errors.get(type(exc).__name__, 0) + 1


async def run(base: str, concurrency: int, duration: float, new_connection: bool) -> dict:
    url = base.rstrip("/") + "/api/v1/analyze"
    latencies: list[float] = []
    errors: dict = {}
    # new_connection: ปิด connection หลังทุกคำขอ ใกล้กับผู้ใช้จริงหลายคนที่ต่างคนต่างเปิด connection ของตัวเอง
    # ถ้าใช้ connection เดิมตลอด (ค่าเริ่มต้นของ httpx) connection ที่ไปตกที่โปรเซสไหนจะติดอยู่กับโปรเซสนั้น
    headers = {"Content-Type": "application/json", **({"Connection": "close"} if new_connection else {})}
    limits = httpx.Limits(max_connections=concurrency, max_keepalive_connections=concurrency)
    async with httpx.AsyncClient(timeout=60, limits=limits) as client:
        # อุ่นเครื่องก่อนจับเวลา ไม่ให้การเชื่อมต่อครั้งแรกปนในผล
        await client.post(url, content=make_payload(), headers={"Content-Type": "application/json"})
        start = time.perf_counter()
        stop_at = start + duration
        await asyncio.gather(*(worker(client, url, stop_at, latencies, errors, headers) for _ in range(concurrency)))
        elapsed = time.perf_counter() - start
    latencies.sort()

    def pct(p: float) -> float:
        return latencies[min(len(latencies) - 1, int(len(latencies) * p))] if latencies else float("nan")

    return {
        "concurrency": concurrency,
        "ok": len(latencies),
        "errors": errors,
        "rps": len(latencies) / elapsed,
        "p50": statistics.median(latencies) if latencies else float("nan"),
        "p95": pct(0.95),
        "p99": pct(0.99),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://localhost:8000")
    parser.add_argument("--concurrency", type=int, nargs="+", default=[1, 10, 50])
    parser.add_argument("--duration", type=float, default=15)
    parser.add_argument("--new-connection", action="store_true", help="เปิด connection ใหม่ทุกคำขอ")
    args = parser.parse_args()

    print(f"{'พร้อมกัน':>8} {'สำเร็จ':>8} {'req/s':>8} {'p50 ms':>9} {'p95 ms':>9} {'p99 ms':>9}  ผิดพลาด")
    for c in args.concurrency:
        r = asyncio.run(run(args.url, c, args.duration, args.new_connection))
        print(f"{r['concurrency']:>8} {r['ok']:>8} {r['rps']:>8.1f} {r['p50']:>9.1f} {r['p95']:>9.1f} "
              f"{r['p99']:>9.1f}  {r['errors'] or '-'}")


if __name__ == "__main__":
    main()
