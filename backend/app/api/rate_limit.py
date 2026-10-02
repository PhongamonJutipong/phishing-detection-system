"""
จำกัดจำนวนคำขอต่อผู้เรียกหนึ่งราย สำหรับ endpoint ที่เปิดสาธารณะ

POST /analyze ไม่มีการยืนยันตัวตน ใครยิงถึงก็เรียกได้ จึงต้องมีเพดานกันทั้งการยิงถล่ม
และการนำระบบไปใช้เป็นบริการฟรีของคนอื่น

ข้อจำกัด: ตัวนับเก็บในหน่วยความจำของโปรเซสเดียว ถ้าขยายเป็นหลาย worker หรือหลาย
instance แต่ละตัวจะนับแยกกัน เพดานจริงจะกลายเป็น limit x จำนวนโปรเซส
เมื่อถึงขั้นนั้นต้องย้ายตัวนับไปไว้ที่ Redis หรือทำที่ reverse proxy แทน

เมื่อมีตัวคั่น (reverse proxy, Cloudflare Tunnel) ต้องตั้ง TRUSTED_PROXIES ด้วย
ไม่งั้นคู่สนทนาจะเป็นตัวคั่นเสมอ ผู้ใช้ทุกคนไปรวมอยู่ในตัวนับถังเดียวกัน
แล้วคนเดียวยิงจนเต็มเพดานทำให้คนอื่นใช้ไม่ได้ทั้งหมด ดู _client_ip()
"""
import hashlib
import ipaddress
import math
import os
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

# จำนวนโปรเซสของ uvicorn (ตั้งผ่าน WEB_CONCURRENCY ใน docker-compose.yml)
_WORKERS = max(1, int(os.environ.get("WEB_CONCURRENCY", "1") or 1))

# สมัคร/เข้าสู่ระบบใช้ตัวนับแยก และเพดานต่ำกว่ามาก เพราะเป็นเป้าของการสุ่มเดารหัสผ่าน
# หารเพดานด้วยจำนวนโปรเซส: ตัวนับอยู่แยกกันในแต่ละโปรเซส ถ้าไม่หาร ผู้โจมตีที่เปิดหลาย connection
# จะเดารหัสผ่านได้ AUTH_RATE_LIMIT x จำนวนโปรเซส ครั้งต่อนาที หารแล้วรวมทุกโปรเซสไม่เกินค่าที่ตั้ง
# (ผู้ใช้ที่ต่อ connection เดิมตลอดจะเจอเพดานเข้มกว่าที่ตั้ง ซึ่งยอมรับได้สำหรับหน้า login)
auth_limiter = RateLimiter(
    limit=math.ceil(settings.auth_rate_limit_per_minute / _WORKERS) if settings.auth_rate_limit_per_minute > 0 else 0,
    max_clients=settings.rate_limit_max_clients,
)


def _parse_trusted_proxies(raw: str) -> list[ipaddress.IPv4Network | ipaddress.IPv6Network]:
    """แปลงรายการ IP/CIDR ที่เชื่อถือได้ ข้ามค่าที่พาร์สไม่ผ่านแทนที่จะทำให้ระบบขึ้นไม่ได้"""
    networks = []
    for item in raw.split(","):
        item = item.strip()
        if not item:
            continue
        try:
            networks.append(ipaddress.ip_network(item, strict=False))
        except ValueError:
            # ค่าผิดรูปแบบ = ไม่เชื่อ ซึ่งปลอดภัยกว่าการเดาว่าผู้ตั้งหมายถึงอะไร
            continue
    return networks


_TRUSTED_PROXIES = _parse_trusted_proxies(settings.trusted_proxies)


def _is_trusted_proxy(host: str) -> bool:
    if not _TRUSTED_PROXIES:
        return False
    try:
        addr = ipaddress.ip_address(host)
    except ValueError:
        return False
    return any(addr in net for net in _TRUSTED_PROXIES)


def _client_ip(request: Request) -> str:
    """
    IP ของผู้ใช้จริง

    ค่าตั้งต้นคือ IP ของคู่สนทนาโดยตรง ซึ่งปลอมไม่ได้เพราะต้องทำ TCP handshake สำเร็จ
    จะหันไปอ่าน header ก็เฉพาะเมื่อคู่สนทนาอยู่ในรายการ trusted_proxies เท่านั้น
    ถ้าเชื่อ header จากใครก็ได้ ผู้โจมตีจะใส่ IP สุ่มทุกคำขอแล้วข้าม rate limit ไปทั้งหมด
    """
    peer = request.client.host if request.client else "unknown"
    if not _is_trusted_proxy(peer):
        return peer

    forwarded = request.headers.get(settings.real_ip_header, "")
    # X-Forwarded-For มีได้หลายค่า ตัวซ้ายสุดคือผู้ใช้ ส่วน CF-Connecting-IP มีค่าเดียว
    candidate = forwarded.split(",")[0].strip()
    if not candidate:
        return peer
    try:
        ipaddress.ip_address(candidate)
    except ValueError:
        # ตัวคั่นที่เชื่อถือได้ส่งค่าเพี้ยนมา ถอยไปใช้ IP ของตัวคั่นดีกว่าเอาค่าขยะไปทำคีย์
        return peer
    return candidate


def _client_key(request: Request) -> str:
    """
    คีย์ของผู้เรียก เก็บเป็นค่าแฮชไม่ใช่ IP ดิบ

    ที่อยู่ IP เป็นข้อมูลส่วนบุคคล การเก็บเพื่อจำกัดอัตราไม่จำเป็นต้องรู้ค่าจริง
    จึงแฮชทิ้งเพื่อไม่ให้มี IP ของผู้ใช้ค้างอยู่ในหน่วยความจำของเซิร์ฟเวอร์
    """
    host = _client_ip(request)
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


def rate_limit_auth(request: Request) -> None:
    if auth_limiter.allow(_client_key(request)):
        return
    raise HTTPException(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        detail="พยายามเข้าสู่ระบบถี่เกินกำหนด กรุณารอสักครู่แล้วลองใหม่",
        headers={"Retry-After": str(auth_limiter.window)},
    )
