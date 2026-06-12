from typing import Generator

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from backend.config import settings
from backend.database import SessionLocal
from backend.core.security import decode_token
from backend.models.user import User
from backend.models.rbac import UserAccountAccess

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    payload = decode_token(token, settings.JWT_SECRET_KEY)
    if not payload or payload.get("type") != "access":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    user = db.query(User).filter(User.id == int(payload.get("sub"))).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive")
    return user


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if not current_user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin required")
    return current_user


def verify_account_access(user: User, account_id: int, db: Session):
    if user.is_admin:
        return
    access = db.query(UserAccountAccess).filter_by(user_id=user.id, account_id=account_id).first()
    if not access:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No access to this account")


def get_accessible_account_ids(user: User, db: Session) -> list[int] | None:
    if user.is_admin:
        return None
    rows = db.query(UserAccountAccess.account_id).filter_by(user_id=user.id).all()
    return [r[0] for r in rows]
