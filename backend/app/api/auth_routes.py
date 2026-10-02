"""
API บัญชีผู้ใช้ (/api/v1/auth/...)

การตรวจอีเมลไม่บังคับให้เข้าสู่ระบบ บัญชีเป็นทางเลือกเท่านั้น
ส่ง token ในรูปแบบ Authorization: Bearer <token>
"""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Header, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.api.rate_limit import rate_limit_auth
from app.config import settings
from app.db.database import get_db
from app.db.models import AppUser
from app.schemas import (
    AuthResponse,
    DeleteAccountRequest,
    GoogleSignInRequest,
    LoginRequest,
    RegisterRequest,
    UserProfile,
)
from app.services.auth_service import (
    AuthService,
    ConsentRequiredError,
    EmailTakenError,
    GoogleSignInDisabledError,
    InvalidCredentialsError,
    InvalidGoogleTokenError,
    PasswordRequiredToLinkError,
    verify_google_id_token,
    verify_password,
)

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


@router.get("/config")
def auth_config():
    """
    ค่าที่หน้าเว็บต้องรู้ตอนทำงาน

    client_id ของ Google ไม่ใช่ความลับ (ถูกฝังในหน้าเว็บอยู่แล้วตามการออกแบบของ Google)
    แต่ต้องส่งตอน runtime ไม่ใช่ตอน build เพราะไฟล์ static ชุดเดียวต้องใช้ได้หลายเครื่อง
    ว่าง = หน้าเว็บจะไม่แสดงปุ่มเข้าสู่ระบบด้วย Google
    """
    return {"google_client_id": settings.google_client_id or None}


@router.post("/google", response_model=AuthResponse, dependencies=[Depends(rate_limit_auth)])
def google_sign_in(body: GoogleSignInRequest, response: Response, db: Session = Depends(get_db)):
    """
    เข้าสู่ระบบด้วยบัญชี Google (สมัครให้เองถ้ายังไม่มีบัญชี)

    ตอบ 201 เมื่อสร้างบัญชีใหม่ และ 200 เมื่อเข้าสู่ระบบบัญชีเดิม
    รหัส error ส่งกลับใน header X-Auth-Reason ให้หน้าเว็บแยกกรณีได้โดยไม่ต้องอ่านข้อความไทย
    """
    service = AuthService(db)
    try:
        email = verify_google_id_token(body.id_token)
    except GoogleSignInDisabledError:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "ระบบนี้ยังไม่ได้เปิดการเข้าสู่ระบบด้วยบัญชี Google",
            headers={"X-Auth-Reason": "GOOGLE_DISABLED"},
        )
    except InvalidGoogleTokenError:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "ยืนยันบัญชี Google ไม่สำเร็จ กรุณาลองใหม่",
            headers={"X-Auth-Reason": "INVALID_GOOGLE_TOKEN"},
        )

    try:
        user, created = service.sign_in_with_google(
            email, accept_privacy_policy=body.accept_privacy_policy, link_password=body.link_password
        )
    except ConsentRequiredError:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "ต้องยอมรับนโยบายความเป็นส่วนตัวก่อนสร้างบัญชี",
            headers={"X-Auth-Reason": "CONSENT_REQUIRED"},
        )
    except PasswordRequiredToLinkError:
        # 409 เพราะอีเมลนี้มีบัญชีอยู่แล้วและต้องทำอีกขั้นก่อน ไม่ใช่ความผิดของ token
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "อีเมลนี้มีบัญชีที่ใช้รหัสผ่านอยู่แล้ว กรุณากรอกรหัสผ่านเดิมหนึ่งครั้งเพื่อผูกกับบัญชี Google",
            headers={"X-Auth-Reason": "PASSWORD_REQUIRED_TO_LINK"},
        )
    except InvalidCredentialsError:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "รหัสผ่านเดิมไม่ถูกต้อง",
            headers={"X-Auth-Reason": "INVALID_LINK_PASSWORD"},
        )
    except EmailTakenError:
        raise HTTPException(status.HTTP_409_CONFLICT, "อีเมลนี้สมัครสมาชิกไว้แล้ว")

    token, expires_at = service.create_session(user, remember=body.remember)
    response.status_code = status.HTTP_201_CREATED if created else status.HTTP_200_OK
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
    """
    ลบบัญชีถาวร ต้องยืนยันตัวตนซ้ำ

    ยืนยันได้สองทาง: รหัสผ่าน หรือ ID token ใบใหม่จาก Google
    บัญชีที่สร้างจาก Google ไม่มีรหัสผ่าน ถ้าไม่มีทางที่สองจะลบบัญชีตัวเองไม่ได้
    """
    service = AuthService(db)
    confirmed = False

    if body.password and verify_password(body.password, user.password_hash):
        confirmed = True
    elif body.id_token:
        try:
            # ต้องเป็นอีเมลของบัญชีที่กำลังเข้าสู่ระบบอยู่ ไม่ใช่ token ของบัญชี Google ใดก็ได้
            email = verify_google_id_token(body.id_token)
            from app.services.auth_service import email_lookup_hash

            confirmed = email_lookup_hash(email) == user.email_hash
        except (GoogleSignInDisabledError, InvalidGoogleTokenError):
            confirmed = False

    if not confirmed:
        # 403 ไม่ใช่ 401 เพราะผู้ใช้เข้าสู่ระบบอยู่แล้ว แค่ยืนยันตัวตนซ้ำไม่ผ่าน
        raise HTTPException(status.HTTP_403_FORBIDDEN, "ยืนยันตัวตนไม่สำเร็จ")
    service.delete_account(user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
