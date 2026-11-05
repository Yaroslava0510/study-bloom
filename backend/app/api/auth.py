import asyncio
import hashlib
import hmac
import secrets
import smtplib
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from passlib.context import CryptContext
from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db import get_db
from app.models import PasswordReset, User, UserSession
from app.schemas.auth import (
    EmailRequest, LoginRequest, RegisterRequest, ResetCompleteRequest,
    ResetVerifyRequest, UserResponse,
)

router = APIRouter(prefix="/api/v1/auth", tags=["authentication"])
password_context = CryptContext(schemes=["argon2"], deprecated="auto")
SESSION_COOKIE = "daybook_session"
CSRF_COOKIE = "daybook_csrf"
RESET_MINUTES = 10
MAX_CODE_ATTEMPTS = 5


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def reset_code_digest(code: str) -> str:
    pepper = settings.reset_code_pepper
    if not pepper:
        raise HTTPException(status_code=503, detail="Восстановление пароля временно недоступно.")
    return hmac.new(pepper.encode("utf-8"), code.encode("ascii"), hashlib.sha256).hexdigest()


def normalize_email(value: str) -> str:
    return value.strip().lower()


def set_auth_cookies(response: Response, session_token: str, csrf_token: str) -> None:
    common = {
        "secure": settings.cookie_secure,
        "samesite": settings.cookie_samesite,
        "max_age": settings.session_days * 24 * 60 * 60,
        "path": "/",
    }
    response.set_cookie(SESSION_COOKIE, session_token, httponly=True, **common)
    response.set_cookie(CSRF_COOKIE, csrf_token, httponly=False, **common)


def clear_auth_cookies(response: Response) -> None:
    response.delete_cookie(
        SESSION_COOKIE, path="/", secure=settings.cookie_secure,
        httponly=True, samesite=settings.cookie_samesite,
    )
    response.delete_cookie(
        CSRF_COOKIE, path="/", secure=settings.cookie_secure,
        httponly=False, samesite=settings.cookie_samesite,
    )


def require_csrf(request: Request) -> None:
    cookie_token = request.cookies.get(CSRF_COOKIE)
    header_token = request.headers.get("X-CSRF-Token")
    if not cookie_token or not header_token or not secrets.compare_digest(cookie_token, header_token):
        raise HTTPException(status_code=403, detail="CSRF validation failed")


async def current_user(
    request: Request, db: AsyncSession = Depends(get_db)
) -> User:
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        raise HTTPException(status_code=401, detail="Authentication required")
    result = await db.execute(
        select(UserSession).where(UserSession.token_hash == digest(token))
    )
    session = result.scalar_one_or_none()
    if not session or session.expires_at <= utc_now():
        raise HTTPException(status_code=401, detail="Session expired")
    user_result = await db.execute(select(User).where(User.id == session.user_id))
    user = user_result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="Account not found")
    return user


async def create_session(user: User, db: AsyncSession, response: Response) -> None:
    token = secrets.token_urlsafe(48)
    csrf = secrets.token_urlsafe(32)
    db.add(UserSession(
        user_id=user.id,
        token_hash=digest(token),
        expires_at=utc_now() + timedelta(days=settings.session_days),
    ))
    await db.commit()
    set_auth_cookies(response, token, csrf)


def send_reset_email(email: str, code: str) -> None:
    if not all([settings.smtp_host, settings.smtp_user, settings.smtp_password]):
        raise RuntimeError("SMTP is not configured")
    message = EmailMessage()
    message["Subject"] = "Код восстановления DAYBOOK"
    message["From"] = settings.smtp_from or settings.smtp_user
    message["To"] = email
    message.set_content(
        f"Твой код восстановления DAYBOOK: {code}\n"
        f"Код действует {RESET_MINUTES} минут и используется один раз. "
        "Если ты не запрашивала восстановление, проигнорируй это письмо."
    )
    if settings.smtp_port == 465:
        with smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port, timeout=20) as smtp:
            smtp.login(settings.smtp_user, settings.smtp_password)
            smtp.send_message(message)
    else:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=20) as smtp:
            smtp.ehlo()
            smtp.starttls()
            smtp.ehlo()
            smtp.login(settings.smtp_user, settings.smtp_password)
            smtp.send_message(message)


@router.get("/csrf")
async def csrf_token(response: Response):
    token = secrets.token_urlsafe(32)
    response.set_cookie(
        CSRF_COOKIE, token, httponly=False, secure=settings.cookie_secure,
        samesite=settings.cookie_samesite, path="/", max_age=3600,
    )
    return {"csrf_token": token}


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    data: RegisterRequest, response: Response, request: Request,
    db: AsyncSession = Depends(get_db),
):
    require_csrf(request)
    email = normalize_email(str(data.email))
    existing = await db.execute(select(User).where(User.contact == email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Этот email уже зарегистрирован")
    user = User(
        contact=email,
        password_hash=password_context.hash(data.password),
        name=data.name.strip(),
    )
    db.add(user)
    await db.flush()
    await create_session(user, db, response)
    return UserResponse(id=user.id, email=user.contact, name=user.name)


@router.post("/login", response_model=UserResponse)
async def login(
    data: LoginRequest, response: Response, request: Request,
    db: AsyncSession = Depends(get_db),
):
    require_csrf(request)
    email = normalize_email(str(data.email))
    result = await db.execute(select(User).where(User.contact == email))
    user = result.scalar_one_or_none()
    if not user or not password_context.verify(data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Неверный email или пароль")
    await create_session(user, db, response)
    return UserResponse(id=user.id, email=user.contact, name=user.name)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    response: Response, request: Request, db: AsyncSession = Depends(get_db),
):
    require_csrf(request)
    token = request.cookies.get(SESSION_COOKIE)
    if token:
        await db.execute(delete(UserSession).where(UserSession.token_hash == digest(token)))
        await db.commit()
    clear_auth_cookies(response)


@router.get("/me", response_model=UserResponse)
async def me(user: User = Depends(current_user)):
    return UserResponse(id=user.id, email=user.contact, name=user.name)


@router.post("/password-reset/request")
async def password_reset_request(data: EmailRequest, db: AsyncSession = Depends(get_db)):
    email = normalize_email(str(data.email))
    result = await db.execute(select(User).where(User.contact == email))
    user = result.scalar_one_or_none()
    # Keep the response identical for existing and unknown accounts.
    if not user:
        return {"ok": True}
    await db.execute(
        update(PasswordReset)
        .where(PasswordReset.user_id == user.id, PasswordReset.used.is_(False))
        .values(used=True)
    )
    code = f"{secrets.randbelow(1_000_000):06d}"
    reset = PasswordReset(
        user_id=user.id, code_hash=reset_code_digest(code),
        expires_at=utc_now() + timedelta(minutes=RESET_MINUTES),
        attempts=0, used=False,
    )
    db.add(reset)
    await db.commit()
    try:
        await asyncio.to_thread(send_reset_email, email, code)
    except Exception:
        reset.used = True
        await db.commit()
        raise HTTPException(status_code=503, detail="Не удалось отправить письмо. Попробуй позже.")
    return {"ok": True}


@router.post("/password-reset/verify")
async def password_reset_verify(data: ResetVerifyRequest, db: AsyncSession = Depends(get_db)):
    email = normalize_email(str(data.email))
    result = await db.execute(
        select(PasswordReset).join(User)
        .where(User.contact == email, PasswordReset.used.is_(False))
        .with_for_update()
        .order_by(PasswordReset.id.desc()).limit(1)
    )
    reset = result.scalar_one_or_none()
    if not reset:
        raise HTTPException(status_code=400, detail="Код недействителен или срок его действия истёк")
    if reset.expires_at <= utc_now():
        reset.used = True
        await db.commit()
        raise HTTPException(status_code=400, detail="Код недействителен или срок его действия истёк")
    if reset.attempts >= MAX_CODE_ATTEMPTS:
        reset.used = True
        await db.commit()
        raise HTTPException(status_code=429, detail="Слишком много попыток. Запроси новый код.")
    if not secrets.compare_digest(reset_code_digest(data.code), reset.code_hash):
        reset.attempts += 1
        if reset.attempts >= MAX_CODE_ATTEMPTS:
            reset.used = True
        await db.commit()
        raise HTTPException(status_code=400, detail="Неверный код")
    token = secrets.token_urlsafe(32)
    reset.token_hash = digest(token)
    await db.commit()
    return {"ok": True, "token": token}


@router.post("/password-reset/complete")
async def password_reset_complete(data: ResetCompleteRequest, db: AsyncSession = Depends(get_db)):
    email = normalize_email(str(data.email))
    result = await db.execute(
        select(PasswordReset).join(User)
        .where(User.contact == email, PasswordReset.used.is_(False))
        .order_by(PasswordReset.id.desc()).limit(1)
    )
    reset = result.scalar_one_or_none()
    if not reset or not reset.token_hash:
        raise HTTPException(status_code=400, detail="Сначала подтверди код из письма")
    if reset.expires_at <= utc_now():
        reset.used = True
        await db.commit()
        raise HTTPException(status_code=400, detail="Срок восстановления истёк. Запроси новый код.")
    if not secrets.compare_digest(digest(data.token), reset.token_hash):
        raise HTTPException(status_code=400, detail="Восстановление недействительно")
    user_result = await db.execute(select(User).where(User.id == reset.user_id))
    user = user_result.scalar_one()
    user.password_hash = password_context.hash(data.password)
    reset.used = True
    await db.execute(delete(UserSession).where(UserSession.user_id == user.id))
    await db.commit()
    return {"ok": True}
