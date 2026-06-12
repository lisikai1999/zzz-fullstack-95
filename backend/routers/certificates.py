from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend.dependencies import get_db, get_current_user, get_accessible_account_ids
from backend.models.user import User
from backend.models.certificate import Certificate
from backend.schemas.certificate import CertificateResponse, CertAlertSummary

router = APIRouter(prefix="/api/v1/certificates", tags=["certificates"])


@router.get("/", response_model=list[CertificateResponse])
def list_certificates(
    account_id: int | None = Query(None),
    alert_level: str | None = Query(None),
    orphan_only: bool = Query(False),
    region: str | None = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    accessible = get_accessible_account_ids(current_user, db)
    query = db.query(Certificate)

    if accessible is not None:
        query = query.filter(Certificate.account_id.in_(accessible))
    if account_id:
        query = query.filter(Certificate.account_id == account_id)
    if alert_level:
        query = query.filter(Certificate.alert_level == alert_level)
    if orphan_only:
        query = query.filter(Certificate.is_orphan == True)
    if region:
        query = query.filter(Certificate.region == region)

    return query.order_by(Certificate.not_after.asc()).offset(skip).limit(limit).all()


@router.get("/alerts", response_model=CertAlertSummary)
def cert_alerts(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    accessible = get_accessible_account_ids(current_user, db)
    query = db.query(Certificate).filter(Certificate.alert_level.isnot(None))

    if accessible is not None:
        query = query.filter(Certificate.account_id.in_(accessible))

    certs = query.order_by(Certificate.not_after.asc()).all()
    return CertAlertSummary(
        critical=[c for c in certs if c.alert_level == "critical"],
        warning=[c for c in certs if c.alert_level == "warning"],
        info=[c for c in certs if c.alert_level == "info"],
    )


@router.get("/orphans", response_model=list[CertificateResponse])
def cert_orphans(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    accessible = get_accessible_account_ids(current_user, db)
    query = db.query(Certificate).filter(Certificate.is_orphan == True)
    if accessible is not None:
        query = query.filter(Certificate.account_id.in_(accessible))
    return query.all()


@router.get("/{cert_id}", response_model=CertificateResponse)
def get_certificate(cert_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    cert = db.query(Certificate).filter(Certificate.id == cert_id).first()
    if not cert:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Certificate not found")
    accessible = get_accessible_account_ids(current_user, db)
    if accessible is not None and cert.account_id not in accessible:
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="No access")
    return cert
