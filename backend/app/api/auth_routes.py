"""
API บัญชีผู้ใช้ (/api/v1/auth/...)

การตรวจอีเมลไม่บังคับให้เข้าสู่ระบบ บัญชีเป็นทางเลือกเท่านั้น
ส่ง token ในรูปแบบ Authorization: Bearer <token>
"""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Header, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.api.rate_limit import rate_limit_auth
from app.db.database import get_db
from app.db.models import AppUser
from app.schemas import AuthResponse, DeleteAccountRequest, LoginRequest, RegisterRequest, UserProfile
from app.services.auth_service import AuthService, EmailTakenError, InvalidCredentialsError, verify_password

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

# ข้อความเดียวกันทั้งกรณีไม่มีบัญชีและรหัสผ่านผิด ไม่ให้ใช้หน้านี้ไล่เช็คว่าอีเมลใดมีบัญชี
_INVALID_CREDENTIALS = "อีเมลหรือรหัสผ่านไม่ถูกต้อง"


def _bearer_token(authorization: str | None) -> str:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "กรุณาเข้าสู่ระบบ", headers={"WWW-Authenticate": "Bearer"})
    return authorization[7:].strip()


def current_user(authorization: str | None = Header(default=None), db: Session = Depends(get_db)) -> AppUser:
    user = AuthService(db).user_for_token(_bearer_token(authorization))
    if user is None:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, "การเข้าสู่ระบบหมดอายุ กรุณาเข้าสู่ระบบใหม่",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def _utc(value: datetime) -> datetime:
    """SQLite คืนเวลาแบบไม่มี timezone เบราว์เซอร์จะตีความเป็นเวลาท้องถิ่นแล้วแสดงคลาด จึงใส่ UTC กำกับ"""
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def _profile(service: AuthService, user: AppUser) -> UserProfile:
    return UserProfile(
        email=service.decrypt_email(user),
        created_at=_utc(user.created_at),
        consent_version=user.consent_version,
        consent_at=_utc(user.consent_at),
    )


@router.post(
    "/register",
    response_model=AuthResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit_auth)],
)
def register(body: RegisterRequest, db: Session = Depends(get_db)):
    """สมัครสมาชิกแล้วเข้าสู่ระบบให้ทันที"""
    service = AuthService(db)
    try:
        user = service.register(body.email, body.password)
    except EmailTakenError:
        # ยอมบอกว่าอีเมลนี้มีบัญชีแล้ว เพราะระบบยังไม่มีการยืนยันอีเมลทางไปรษณีย์อิเล็กทรอนิกส์
        # ถ้าไม่บอก ผู้ใช้จริงจะไม่รู้ว่าทำไมสมัครไม่ได้ ความเสี่ยงที่เหลือจำกัดด้วย rate limit
        raise HTTPException(status.HTTP_409_CONFLICT, "อีเมลนี้สมัครสมาชิกไว้แล้ว")
    token, expires_at = service.create_session(user)
    return AuthResponse(token=token, expires_at=expires_at, user=_profile(service, user))


@router.post("/login", response_model=AuthResponse, dependencies=[Depends(rate_limit_auth)])
def login(body: LoginRequest, db: Session = Depends(get_db)):
    service = AuthService(db)
    try:
        user = service.authenticate(body.email, body.password)
    except InvalidCredentialsError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, _INVALID_CREDENTIALS)
    token, expires_at = service.create_session(user, remember=body.remember)
    return AuthResponse(token=token, expires_at=expires_at, user=_profile(service, user))


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(authorization: str | None = Header(default=None), db: Session = Depends(get_db)):
    """ยกเลิก token นี้ที่ฝั่งเซิร์ฟเวอร์ ไม่ใช่แค่ลบในเบราว์เซอร์ token ที่หลุดไปจึงใช้ต่อไม่ได้"""
    AuthService(db).revoke_session(_bearer_token(authorization))
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/me", response_model=UserProfile)
def me(user: AppUser = Depends(current_user), db: Session = Depends(get_db)):
    """ข้อมูลทั้งหมดที่ระบบเก็บเกี่ยวกับบัญชีนี้"""
    return _profile(AuthService(db), user)


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(rate_limit_auth)])
def delete_account(body: DeleteAccountRequest, user: AppUser = Depends(current_user), db: Session = Depends(get_db)):
    """ลบบัญชีถาวร ต้องยืนยันด้วยรหัสผ่าน"""
    if not verify_password(body.password, user.password_hash):
        # 403 ไม่ใช่ 401 เพราะผู้ใช้เข้าสู่ระบบอยู่แล้ว แค่ยืนยันรหัสผ่านไม่ผ่าน
        raise HTTPException(status.HTTP_403_FORBIDDEN, "รหัสผ่านไม่ถูกต้อง")
    AuthService(db).delete_account(user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
