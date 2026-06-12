from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.dependencies import get_db, require_admin
from backend.core.security import hash_password
from backend.models.user import User
from backend.models.rbac import UserAccountAccess
from backend.schemas.auth import UserResponse, UserCreate, UserUpdate
from backend.schemas.account import AccountAccessUpdate

router = APIRouter(prefix="/api/v1/users", tags=["users"])


@router.get("/", response_model=list[UserResponse])
def list_users(db: Session = Depends(get_db), _: User = Depends(require_admin)):
    return db.query(User).all()


@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(req: UserCreate, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    if db.query(User).filter((User.username == req.username) | (User.email == req.email)).first():
        raise HTTPException(status_code=400, detail="Username or email already exists")
    user = User(
        username=req.username,
        email=req.email,
        hashed_password=hash_password(req.password),
        is_admin=req.is_admin,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.get("/{user_id}", response_model=UserResponse)
def get_user(user_id: int, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.put("/{user_id}", response_model=UserResponse)
def update_user(user_id: int, req: UserUpdate, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if req.email is not None:
        user.email = req.email
    if req.is_active is not None:
        user.is_active = req.is_active
    if req.is_admin is not None:
        user.is_admin = req.is_admin
    if req.password is not None:
        user.hashed_password = hash_password(req.password)
    db.commit()
    db.refresh(user)
    return user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(user_id: int, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.is_active = False
    db.commit()


@router.put("/{user_id}/accounts")
def set_user_accounts(user_id: int, req: AccountAccessUpdate, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    db.query(UserAccountAccess).filter_by(user_id=user_id).delete()
    for aid in req.account_ids:
        db.add(UserAccountAccess(user_id=user_id, account_id=aid))
    db.commit()
    return {"status": "ok", "account_ids": req.account_ids}


@router.get("/{user_id}/accounts")
def get_user_accounts(user_id: int, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    rows = db.query(UserAccountAccess).filter_by(user_id=user_id).all()
    return {"account_ids": [r.account_id for r in rows]}
