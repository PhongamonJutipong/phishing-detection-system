"""
จำกัดจำนวนคำขอต่อผู้เรียกหนึ่งราย สำหรับ endpoint ที่เปิดสาธารณะ

POST /analyze ไม่มีการยืนยันตัวตน ใครยิงถึงก็เรียกได้ จึงต้องมีเพดานกันทั้งการยิงถล่ม
และการนำระบบไปใช้เป็นบริการฟรีของคนอื่น

ข้อจำกัด: ตัวนับเก็บในหน่วยความจำของโปรเซสเดียว ถ้าขยายเป็นหลาย worker หรือหลาย
instance แต่ละตัวจะนับแยกกัน เพดานจริงจะกลายเป็น limit x จำนวนโปรเซส
เมื่อถึงขั้นนั้นต้องย้ายตัวนับไปไว้ที่ Redis หรือทำที่ reverse proxy แทน
"""
import hashlib
import time
from collections import deque

from fastapi import HTTPException, Request, status

from app.config import settings


class RateLimiter:
    """นับคำขอแบบ sliding window ต่อหนึ่งคีย์"""

    def __init__(self, limit: int, window_seconds: int = 60, max_clients: int = 10000):
        self.limit = limit
        self.window = window_seconds
        self.max_clients = max_clients
        self._hits: dict[str, deque[float]] = {}

    def allow(self, key: str, now: float | None = None) -> bool:
        if self.limit <= 0:          # 0 = ปิดการจำกัด
            return True
        now = time.monotonic() if now is None else now
        hits = self._hits.get(key)
        if hits is None:
            self._evict_stale(now)
            hits = self._hits[key] = deque()

        cutoff = now - self.window
        while hits and hits[0] <= cutoff:
            hits.popleft()
        if len(hits) >= self.limit:
            return False
        hits.append(now)
        return True

    def _evict_stale(self, now: float) -> None:
        """กันไม่ให้ตารางโตไม่จำกัดเมื่อมี IP เข้ามาจำนวนมาก"""
        if len(self._hits) < self.max_clients:
            return
        cutoff = now - self.window
        for key in [k for k, v in self._hits.items() if not v or v[-1] <= cutoff]:
            del self._hits[key]
        while len(self._hits) >= self.max_clients:
            oldest = min(self._hits, key=lambda k: self._hits[k][-1])
            del self._hits[oldest]

    def reset(self) -> None:
        self._hits.clear()


analyze_limiter = RateLimiter(
    limit=settings.analyze_rate_limit_per_minute,
    max_clients=settings.rate_limit_max_clients,
)


def _client_key(request: Request) -> str:
    """
    คีย์ของผู้เรียก เก็บเป็นค่าแฮชไม่ใช่ IP ดิบ

    ที่อยู่ IP เป็นข้อมูลส่วนบุคคล การเก็บเพื่อจำกัดอัตราไม่จำเป็นต้องรู้ค่าจริง
    จึงแฮชทิ้งเพื่อไม่ให้มี IP ของผู้ใช้ค้างอยู่ในหน่วยความจำของเซิร์ฟเวอร์
    """
    host = request.client.host if request.client else "unknown"
    pepper = settings.hash_pepper or settings.encryption_key or "no-pepper"
    return hashlib.sha256(f"{pepper}|{host}".encode("utf-8")).hexdigest()[:32]


def rate_limit_analyze(request: Request) -> None:
    if analyze_limiter.allow(_client_key(request)):
        return
    raise HTTPException(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        detail="ส่งคำขอถี่เกินกำหนด กรุณารอสักครู่แล้วลองใหม่",
        headers={"Retry-After": str(analyze_limiter.window)},
    )
