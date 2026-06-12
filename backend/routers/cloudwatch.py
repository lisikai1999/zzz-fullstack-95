from datetime import datetime, timezone, timedelta
from typing import Any

from fastapi import APIRouter, Depends, Query, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.config import settings
from backend.dependencies import get_db, get_current_user, verify_account_access
from backend.models.user import User
from backend.models.aws_account import AWSAccount
from backend.aws.client_factory import AWSClientFactory
from backend.aws.cloudwatch import get_metric_data, get_log_events, build_console_url, METRIC_PRESETS
from backend.schemas.cloudwatch import MetricResponse, MetricDataPoint, LogResponse, LogEvent, ConsoleUrlResponse

router = APIRouter(prefix="/api/v1/cloudwatch", tags=["cloudwatch"])


class MetricQueryRequest(BaseModel):
    account_id: int
    region: str
    metric_key: str
    dimensions: list[dict[str, str]]
    period: int = 300
    hours: int = 3


@router.post("/query-metric", response_model=MetricResponse)
def query_metric_by_context(
    req: MetricQueryRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Accepts pre-resolved dimensions from /context endpoint — frontend fills nothing manually."""
    verify_account_access(current_user, req.account_id, db)

    if req.metric_key not in METRIC_PRESETS:
        raise HTTPException(status_code=400, detail=f"Unknown metric_key. Available: {list(METRIC_PRESETS.keys())}")

    account = db.query(AWSAccount).filter_by(id=req.account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    factory = AWSClientFactory(settings.SECRET_KEY)
    end = datetime.now(timezone.utc)
    start = end - timedelta(hours=req.hours)

    data = get_metric_data(factory, account, req.region, req.metric_key, req.dimensions, req.period, start, end)
    return MetricResponse(
        metric_key=req.metric_key,
        resource_arn="",
        data_points=[MetricDataPoint(timestamp=dp["timestamp"], value=dp["value"]) for dp in data],
    )


@router.get("/metrics", response_model=MetricResponse)
def query_metrics(
    account_id: int = Query(...),
    resource_id: str = Query(...),
    resource_type: str = Query(...),
    metric_key: str = Query(...),
    region: str = Query(...),
    period: int = Query(300),
    hours: int = Query(3),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    verify_account_access(current_user, account_id, db)

    if metric_key not in METRIC_PRESETS:
        raise HTTPException(status_code=400, detail=f"Unknown metric_key. Available: {list(METRIC_PRESETS.keys())}")

    account = db.query(AWSAccount).filter_by(id=account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    factory = AWSClientFactory(settings.SECRET_KEY)
    end = datetime.now(timezone.utc)
    from datetime import timedelta
    start = end - timedelta(hours=hours)

    dimensions = _build_dimensions(resource_type, resource_id)

    data = get_metric_data(factory, account, region, metric_key, dimensions, period, start, end)
    return MetricResponse(
        metric_key=metric_key,
        resource_arn=resource_id,
        data_points=[MetricDataPoint(timestamp=dp["timestamp"], value=dp["value"]) for dp in data],
    )


@router.get("/logs", response_model=LogResponse)
def query_logs(
    account_id: int = Query(...),
    log_group: str = Query(...),
    region: str = Query(...),
    filter_pattern: str = Query(""),
    hours: int = Query(1),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    verify_account_access(current_user, account_id, db)

    account = db.query(AWSAccount).filter_by(id=account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    factory = AWSClientFactory(settings.SECRET_KEY)
    end = datetime.now(timezone.utc)
    from datetime import timedelta
    start = end - timedelta(hours=hours)

    events = get_log_events(factory, account, region, log_group, filter_pattern, start, end, limit)
    return LogResponse(
        log_group=log_group,
        events=[LogEvent(timestamp=e["timestamp"], message=e["message"]) for e in events],
    )


@router.get("/console-url", response_model=ConsoleUrlResponse)
def get_console_url(
    region: str = Query(...),
    resource_type: str = Query(...),
    resource_id: str = Query(...),
):
    url = build_console_url(region, resource_type, resource_id)
    return ConsoleUrlResponse(url=url)


def _build_dimensions(resource_type: str, resource_id: str) -> list[dict]:
    if resource_type == "alb":
        arn_suffix = resource_id.split("loadbalancer/")[-1] if "loadbalancer/" in resource_id else resource_id
        return [{"Name": "LoadBalancer", "Value": arn_suffix}]
    elif resource_type == "ecs_service":
        parts = resource_id.split("/")
        if len(parts) >= 3:
            return [
                {"Name": "ClusterName", "Value": parts[-2]},
                {"Name": "ServiceName", "Value": parts[-1]},
            ]
        return [{"Name": "ServiceName", "Value": parts[-1]}]
    elif resource_type == "rds_instance":
        name = resource_id.split(":")[-1] if ":" in resource_id else resource_id
        return [{"Name": "DBInstanceIdentifier", "Value": name}]
    elif resource_type == "elasticache_cluster":
        name = resource_id.split(":")[-1] if ":" in resource_id else resource_id
        return [{"Name": "CacheClusterId", "Value": name}]
    elif resource_type == "ec2_instance":
        return [{"Name": "InstanceId", "Value": resource_id}]
    return []
