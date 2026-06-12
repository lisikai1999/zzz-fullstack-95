import json
import logging
from datetime import datetime, timezone

from backend.config import settings
from backend.database import SessionLocal
from backend.aws.client_factory import AWSClientFactory
from backend.aws.resources import (
    fetch_ec2_instances,
    fetch_rds_instances,
    fetch_ecs_services,
    fetch_albs,
    fetch_elasticache_clusters,
)
from backend.models.aws_account import AWSAccount
from backend.models.resource import Resource
from backend.models.sync_log import SyncLog

logger = logging.getLogger(__name__)


def sync_all_resources():
    db = SessionLocal()
    try:
        accounts = db.query(AWSAccount).filter(AWSAccount.is_active == True).all()
        for account in accounts:
            _sync_account_resources(account, db)
    except Exception as e:
        logger.error(f"Resource sync error: {e}")
    finally:
        db.close()


def _sync_account_resources(account: AWSAccount, db):
    log = SyncLog(account_id=account.id, job_type="resources", status="running")
    db.add(log)
    db.commit()

    try:
        factory = AWSClientFactory(settings.SECRET_KEY)
        all_resources = []
        fetch_results = {
            "ec2_instance": fetch_ec2_instances(factory, account),
            "rds_instance": fetch_rds_instances(factory, account),
            "ecs_service": fetch_ecs_services(factory, account),
            "alb": fetch_albs(factory, account),
            "elasticache_cluster": fetch_elasticache_clusters(factory, account),
        }

        successfully_fetched_types = set()
        for rtype, resources in fetch_results.items():
            all_resources.extend(resources)
            if resources is not None:
                successfully_fetched_types.add(rtype)

        now = datetime.now(timezone.utc)

        for res in all_resources:
            tags = res.get("tags", [])
            is_untagged = len(tags) == 0 or (
                len(tags) == 1 and tags[0].get("Key") == "Name"
            )

            existing = db.query(Resource).filter_by(
                account_id=account.id,
                resource_type=res["resource_type"],
                resource_id=res["resource_id"],
            ).first()

            if existing:
                existing.resource_name = res.get("resource_name")
                existing.region = res["region"]
                existing.tags = json.dumps(tags)
                existing.metadata_json = json.dumps(res.get("metadata", {}))
                existing.status = res.get("status")
                existing.is_untagged = is_untagged
                existing.last_synced_at = now
            else:
                db.add(Resource(
                    account_id=account.id,
                    resource_type=res["resource_type"],
                    resource_id=res["resource_id"],
                    resource_name=res.get("resource_name"),
                    region=res["region"],
                    tags=json.dumps(tags),
                    metadata_json=json.dumps(res.get("metadata", {})),
                    status=res.get("status"),
                    is_untagged=is_untagged,
                    last_synced_at=now,
                ))

        for rtype in successfully_fetched_types:
            db.query(Resource).filter(
                Resource.account_id == account.id,
                Resource.resource_type == rtype,
                Resource.last_synced_at < now,
            ).delete(synchronize_session=False)

        account.last_sync_at = now
        log.status = "success"
        log.finished_at = now
        log.items_synced = len(all_resources)
        db.commit()

    except Exception as e:
        log.status = "failed"
        log.finished_at = datetime.now(timezone.utc)
        log.error_message = str(e)
        db.commit()
        logger.error(f"Sync failed for account {account.account_id}: {e}")
