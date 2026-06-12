import json
import logging
from datetime import datetime, timezone

from backend.config import settings
from backend.database import SessionLocal
from backend.aws.client_factory import AWSClientFactory
from backend.aws.acm import fetch_acm_certificates
from backend.models.aws_account import AWSAccount
from backend.models.certificate import Certificate
from backend.models.sync_log import SyncLog

logger = logging.getLogger(__name__)


def check_all_certificates():
    db = SessionLocal()
    try:
        accounts = db.query(AWSAccount).filter(AWSAccount.is_active == True).all()
        for account in accounts:
            _sync_account_certificates(account, db)
    except Exception as e:
        logger.error(f"Certificate check error: {e}")
    finally:
        db.close()


def _sync_account_certificates(account: AWSAccount, db):
    log = SyncLog(account_id=account.id, job_type="certificates", status="running")
    db.add(log)
    db.commit()

    try:
        factory = AWSClientFactory(settings.SECRET_KEY)
        certs = fetch_acm_certificates(factory, account)
        now = datetime.now(timezone.utc)

        synced_arns = set()
        for cert_data in certs:
            arn = cert_data["certificate_arn"]
            synced_arns.add(arn)

            not_after = cert_data["not_after"]
            if not_after and not isinstance(not_after, datetime):
                not_after = datetime.fromisoformat(str(not_after))

            days_remaining = (not_after - now).days if not_after else 9999
            alert_level = None
            if days_remaining <= 7:
                alert_level = "critical"
            elif days_remaining <= 15:
                alert_level = "warning"
            elif days_remaining <= 30:
                alert_level = "info"

            in_use_by = cert_data.get("in_use_by", [])
            is_orphan = cert_data["status"] == "ISSUED" and len(in_use_by) == 0

            not_before = cert_data.get("not_before")
            if not_before and not isinstance(not_before, datetime):
                not_before = datetime.fromisoformat(str(not_before))

            existing = db.query(Certificate).filter_by(
                account_id=account.id,
                certificate_arn=arn,
            ).first()

            if existing:
                existing.domain_name = cert_data["domain_name"]
                existing.san_names = json.dumps(cert_data.get("san_names", []))
                existing.status = cert_data["status"]
                existing.issuer = cert_data.get("issuer")
                existing.not_before = not_before
                existing.not_after = not_after
                existing.in_use_by = json.dumps(in_use_by)
                existing.is_orphan = is_orphan
                existing.alert_level = alert_level
                existing.region = cert_data["region"]
                existing.last_synced_at = now
            else:
                db.add(Certificate(
                    account_id=account.id,
                    certificate_arn=arn,
                    domain_name=cert_data["domain_name"],
                    san_names=json.dumps(cert_data.get("san_names", [])),
                    status=cert_data["status"],
                    issuer=cert_data.get("issuer"),
                    not_before=not_before,
                    not_after=not_after,
                    in_use_by=json.dumps(in_use_by),
                    is_orphan=is_orphan,
                    alert_level=alert_level,
                    region=cert_data["region"],
                    last_synced_at=now,
                ))

        db.query(Certificate).filter(
            Certificate.account_id == account.id,
            Certificate.certificate_arn.notin_(synced_arns) if synced_arns else True,
        ).delete(synchronize_session=False)

        log.status = "success"
        log.finished_at = now
        log.items_synced = len(certs)
        db.commit()

    except Exception as e:
        log.status = "failed"
        log.finished_at = datetime.now(timezone.utc)
        log.error_message = str(e)
        db.commit()
        logger.error(f"Certificate sync failed for account {account.account_id}: {e}")
