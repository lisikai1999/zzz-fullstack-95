from datetime import datetime, timezone, timedelta

from backend.aws.client_factory import AWSClientFactory
from backend.models.aws_account import AWSAccount


METRIC_PRESETS = {
    "alb_5xx": {
        "namespace": "AWS/ApplicationELB",
        "metric_name": "HTTPCode_ELB_5XX_Count",
        "stat": "Sum",
    },
    "alb_requests": {
        "namespace": "AWS/ApplicationELB",
        "metric_name": "RequestCount",
        "stat": "Sum",
    },
    "ecs_cpu": {
        "namespace": "AWS/ECS",
        "metric_name": "CPUUtilization",
        "stat": "Average",
    },
    "ecs_memory": {
        "namespace": "AWS/ECS",
        "metric_name": "MemoryUtilization",
        "stat": "Average",
    },
    "rds_connections": {
        "namespace": "AWS/RDS",
        "metric_name": "DatabaseConnections",
        "stat": "Average",
    },
    "rds_cpu": {
        "namespace": "AWS/RDS",
        "metric_name": "CPUUtilization",
        "stat": "Average",
    },
    "cache_hit_rate": {
        "namespace": "AWS/ElastiCache",
        "metric_name": "CacheHitRate",
        "stat": "Average",
    },
    "cache_connections": {
        "namespace": "AWS/ElastiCache",
        "metric_name": "CurrConnections",
        "stat": "Average",
    },
    "ec2_cpu": {
        "namespace": "AWS/EC2",
        "metric_name": "CPUUtilization",
        "stat": "Average",
    },
}


def get_metric_data(
    factory: AWSClientFactory,
    account: AWSAccount,
    region: str,
    metric_key: str,
    dimensions: list[dict],
    period: int = 300,
    start: datetime | None = None,
    end: datetime | None = None,
) -> list[dict]:
    preset = METRIC_PRESETS.get(metric_key)
    if not preset:
        return []

    if not end:
        end = datetime.now(timezone.utc)
    if not start:
        start = end - timedelta(hours=3)

    client = factory.get_client(account, "cloudwatch", region)
    resp = client.get_metric_statistics(
        Namespace=preset["namespace"],
        MetricName=preset["metric_name"],
        Dimensions=dimensions,
        StartTime=start,
        EndTime=end,
        Period=period,
        Statistics=[preset["stat"]],
    )

    data_points = []
    for dp in sorted(resp.get("Datapoints", []), key=lambda x: x["Timestamp"]):
        data_points.append({
            "timestamp": dp["Timestamp"].isoformat(),
            "value": dp.get(preset["stat"], 0),
        })
    return data_points


def get_log_events(
    factory: AWSClientFactory,
    account: AWSAccount,
    region: str,
    log_group: str,
    filter_pattern: str = "",
    start: datetime | None = None,
    end: datetime | None = None,
    limit: int = 100,
) -> list[dict]:
    if not end:
        end = datetime.now(timezone.utc)
    if not start:
        start = end - timedelta(hours=1)

    client = factory.get_client(account, "logs", region)
    kwargs = {
        "logGroupName": log_group,
        "startTime": int(start.timestamp() * 1000),
        "endTime": int(end.timestamp() * 1000),
        "limit": limit,
    }
    if filter_pattern:
        kwargs["filterPattern"] = filter_pattern

    resp = client.filter_log_events(**kwargs)
    events = []
    for event in resp.get("events", []):
        events.append({
            "timestamp": datetime.fromtimestamp(event["timestamp"] / 1000, tz=timezone.utc).isoformat(),
            "message": event["message"],
        })
    return events


def build_console_url(region: str, resource_type: str, resource_id: str) -> str:
    base = f"https://{region}.console.aws.amazon.com"
    if resource_type == "alb":
        return f"{base}/ec2/home?region={region}#LoadBalancer:loadBalancerArn={resource_id}"
    elif resource_type == "ecs_service":
        return f"{base}/ecs/home?region={region}#/services"
    elif resource_type == "rds_instance":
        name = resource_id.split(":")[-1] if ":" in resource_id else resource_id
        return f"{base}/rds/home?region={region}#database:id={name}"
    elif resource_type == "ec2_instance":
        return f"{base}/ec2/home?region={region}#InstanceDetails:instanceId={resource_id}"
    elif resource_type == "elasticache_cluster":
        return f"{base}/elasticache/home?region={region}#/redis"
    return f"{base}/cloudwatch/home?region={region}"
