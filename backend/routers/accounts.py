from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.config import settings
from backend.dependencies import get_db, get_current_user, require_admin, get_accessible_account_ids
from backend.core.encryption import encrypt_value, decrypt_value
from backend.models.user import User
from backend.models.aws_account import AWSAccount
from backend.schemas.account import AWSAccountCreate, AWSAccountUpdate, AWSAccountResponse

router = APIRouter(prefix="/api/v1/accounts", tags=["accounts"])


@router.get("/", response_model=list[AWSAccountResponse])
def list_accounts(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    accessible = get_accessible_account_ids(current_user, db)
    query = db.query(AWSAccount)
    if accessible is not None:
        query = query.filter(AWSAccount.id.in_(accessible))
    return query.all()


@router.post("/", response_model=AWSAccountResponse, status_code=status.HTTP_201_CREATED)
def create_account(req: AWSAccountCreate, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    if db.query(AWSAccount).filter(AWSAccount.account_id == req.account_id).first():
        raise HTTPException(status_code=400, detail="Account already exists")
    account = AWSAccount(
        account_id=req.account_id,
        account_name=req.account_name,
        access_key_encrypted=encrypt_value(req.access_key, settings.SECRET_KEY),
        secret_key_encrypted=encrypt_value(req.secret_key, settings.SECRET_KEY),
        default_region=req.default_region,
    )
    db.add(account)
    db.commit()
    db.refresh(account)
    return account


@router.get("/{account_id}", response_model=AWSAccountResponse)
def get_account(account_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    from backend.dependencies import verify_account_access
    verify_account_access(current_user, account_id, db)
    account = db.query(AWSAccount).filter(AWSAccount.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    return account


@router.put("/{account_id}", response_model=AWSAccountResponse)
def update_account(account_id: int, req: AWSAccountUpdate, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    account = db.query(AWSAccount).filter(AWSAccount.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    if req.account_name is not None:
        account.account_name = req.account_name
    if req.access_key is not None:
        account.access_key_encrypted = encrypt_value(req.access_key, settings.SECRET_KEY)
    if req.secret_key is not None:
        account.secret_key_encrypted = encrypt_value(req.secret_key, settings.SECRET_KEY)
    if req.default_region is not None:
        account.default_region = req.default_region
    if req.is_active is not None:
        account.is_active = req.is_active
    db.commit()
    db.refresh(account)
    return account


@router.delete("/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_account(account_id: int, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    account = db.query(AWSAccount).filter(AWSAccount.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    db.delete(account)
    db.commit()


@router.post("/{account_id}/test-connection")
def test_connection(account_id: int, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    account = db.query(AWSAccount).filter(AWSAccount.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    try:
        from backend.aws.client_factory import AWSClientFactory
        factory = AWSClientFactory(settings.SECRET_KEY)
        sts = factory.get_client(account, "sts")
        identity = sts.get_caller_identity()
        return {"status": "ok", "account": identity["Account"], "arn": identity["Arn"]}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Connection failed: {str(e)}")
