from datetime import datetime, timedelta, timezone
from typing import Any, Optional
from jose import jwt, JWTError # type: ignore
from passlib.context import CryptContext # type: ignore
from app.core.config import settings # type: ignore

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(plain: str) -> str:
    return pwd_context.hash(plain)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)

def _expire_at(minutes: int = 15) -> datetime:
    return datetime.now(tz=timezone.utc) + timedelta(minutes=minutes)

def _expire_days(days: int = 7) -> datetime:
    return datetime.now(tz=timezone.utc) + timedelta(days=days)

def create_access_token(subject: str, extra: Optional[dict[str, Any]] = None) -> str:
    to_encode = {"sub": subject, "exp": _expire_at(settings.ACCESS_TOKEN_MINUTES)}
    if extra:
        to_encode.update(extra)
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

def create_refresh_token(subject: str) -> str:
    to_encode = {"sub": subject, "exp": _expire_days(settings.REFRESH_TOKEN_DAYS), "type":"refresh"}
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

def decode_token(token: str) -> dict[str, Any]:
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
