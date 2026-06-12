from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.dependencies import get_db, require_admin
from backend.models.user import User
from backend.models.aws_account import AWSAccount
from backend.models.sync_log import SyncLog

router = APIRouter(prefix="/api/v1/sync", tags=["sync"])


@router.get("/status")
def sync_status(db: Session = Depends(get_db), _: User = Depends(require_admin)):
    accounts = db.query(AWSAccount).filter(AWSAccount.is_active == True).all()
    result = []
    for account in accounts:
        last_log = db.query(SyncLog).filter_by(account_id=account.id).order_by(SyncLog.started_at.desc()).first()
        result.append({
            "account_id": account.id,
            "account_name": account.account_name,
            "last_sync": last_log.started_at.isoformat() if last_log else None,
            "last_status": last_log.status if last_log else None,
            "last_job_type": last_log.job_type if last_log else None,
        })
    return result


@router.get("/logs")
def sync_logs(
    limit: int = 50,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    logs = db.query(SyncLog).order_by(SyncLog.started_at.desc()).limit(limit).all()
    return [
        {
            "id": log.id,
            "account_id": log.account_id,
            "job_type": log.job_type,
            "status": log.status,
            "started_at": log.started_at.isoformat() if log.started_at else None,
            "finished_at": log.finished_at.isoformat() if log.finished_at else None,
            "error_message": log.error_message,
            "items_synced": log.items_synced,
        }
        for log in logs
    ]


@router.post("/trigger")
def trigger_sync(db: Session = Depends(get_db), _: User = Depends(require_admin)):
    from backend.scheduler.jobs.sync_resources import sync_all_resources
    from backend.scheduler.jobs.sync_topology import sync_all_topologies
    from backend.scheduler.jobs.check_certificates import check_all_certificates
    import threading

    def _run():
        sync_all_resources()
        sync_all_topologies()
        check_all_certificates()

    threading.Thread(target=_run, daemon=True).start()
    return {"status": "sync triggered"}
