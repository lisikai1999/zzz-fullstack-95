from datetime import datetime, timedelta, timezone

from jose import jwt, JWTError
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(data: dict, secret: str, expires_minutes: int) -> str:
    to_encode = data.copy()
    to_encode["exp"] = datetime.now(timezone.utc) + timedelta(minutes=expires_minutes)
    to_encode["type"] = "access"
    return jwt.encode(to_encode, secret, algorithm="HS256")


def create_refresh_token(data: dict, secret: str, expires_days: int) -> str:
    to_encode = data.copy()
    to_encode["exp"] = datetime.now(timezone.utc) + timedelta(days=expires_days)
    to_encode["type"] = "refresh"
    return jwt.encode(to_encode, secret, algorithm="HS256")


def decode_token(token: str, secret: str) -> dict | None:
    try:
        return jwt.decode(token, secret, algorithms=["HS256"])
    except JWTError:
        return None
