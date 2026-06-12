from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.config import settings
from backend.dependencies import get_db, get_current_user
from backend.core.security import (
    verify_password,
    hash_password,
    create_access_token,
    create_refresh_token,
    decode_token,
)
from backend.models.user import User
from backend.schemas.auth import (
    LoginRequest,
    TokenResponse,
    RefreshRequest,
    UserResponse,
)

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
def login(req: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == req.username).first()
    if not user or not verify_password(req.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account disabled")
    access_token = create_access_token(
        {"sub": str(user.id)}, settings.JWT_SECRET_KEY, settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES
    )
    refresh_token = create_refresh_token(
        {"sub": str(user.id)}, settings.JWT_SECRET_KEY, settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS
    )
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/refresh", response_model=TokenResponse)
def refresh(req: RefreshRequest, db: Session = Depends(get_db)):
    payload = decode_token(req.refresh_token, settings.JWT_SECRET_KEY)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")
    user = db.query(User).filter(User.id == int(payload.get("sub"))).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    access_token = create_access_token(
        {"sub": str(user.id)}, settings.JWT_SECRET_KEY, settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES
    )
    refresh_token = create_refresh_token(
        {"sub": str(user.id)}, settings.JWT_SECRET_KEY, settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS
    )
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.get("/me", response_model=UserResponse)
def me(current_user: User = Depends(get_current_user)):
    return current_user
