import json
import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.dependencies import get_db, get_current_user, verify_account_access
from backend.models.user import User
from backend.models.topology import TopologyNode, TopologyEdge
from backend.models.aws_account import AWSAccount
from backend.models.resource import Resource
from backend.schemas.topology import (
    TopologyGraphResponse,
    TopologyNodeResponse,
    TopologyEdgeResponse,
    NodeHealthResponse,
    ReverseLookupResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/topology", tags=["topology"])


@router.get("/{account_id}/graph", response_model=TopologyGraphResponse)
def get_topology_graph(account_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    verify_account_access(current_user, account_id, db)

    nodes = db.query(TopologyNode).filter_by(account_id=account_id).all()
    edges = db.query(TopologyEdge).filter_by(account_id=account_id).all()

    node_responses = []
    for n in nodes:
        meta = json.loads(n.metadata_json) if n.metadata_json else None
        node_responses.append(TopologyNodeResponse(
            id=f"{n.node_type}:{n.node_id}",
            label=n.node_name or n.node_id,
            node_type=n.node_type,
            region=n.region,
            metadata=meta,
        ))

    node_id_map = {n.id: f"{n.node_type}:{n.node_id}" for n in nodes}
    edge_responses = [
        TopologyEdgeResponse(
            source=node_id_map.get(e.source_node_id, ""),
            target=node_id_map.get(e.target_node_id, ""),
            edge_type=e.edge_type,
        )
        for e in edges
        if e.source_node_id in node_id_map and e.target_node_id in node_id_map
    ]

    return TopologyGraphResponse(nodes=node_responses, edges=edge_responses)


@router.get("/{account_id}/nodes/by-node-id")
def get_node_by_identifiers(
    account_id: int,
    node_type: str = Query(...),
    node_id: str = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Look up a topology node by type+node_id and return full context for the ops console."""
    verify_account_access(current_user, account_id, db)
    node = db.query(TopologyNode).filter_by(account_id=account_id, node_type=node_type, node_id=node_id).first()
    if not node:
        node = db.query(TopologyNode).filter(
            TopologyNode.account_id == account_id,
            TopologyNode.node_type == node_type,
            TopologyNode.node_id.contains(node_id),
        ).first()
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")

    meta = json.loads(node.metadata_json) if node.metadata_json else {}
    context = {
        "node_id": node.id,
        "node_type": node.node_type,
        "node_name": node.node_name or node.node_id,
        "resource_id": node.node_id,
        "region": node.region,
        "account_id": account_id,
        "metrics": _resolve_metrics(node, meta),
        "log_groups": _resolve_log_groups(node, meta, db, account_id),
        "console_url": _resolve_console_url(node, meta),
        "upstream": [],
        "downstream": [],
    }

    upstream_edges = db.query(TopologyEdge).filter_by(target_node_id=node.id).all()
    for edge in upstream_edges:
        src = db.query(TopologyNode).filter_by(id=edge.source_node_id).first()
        if src:
            context["upstream"].append({"id": src.id, "type": src.node_type, "name": src.node_name or src.node_id})

    downstream_edges = db.query(TopologyEdge).filter_by(source_node_id=node.id).all()
    for edge in downstream_edges:
        tgt = db.query(TopologyNode).filter_by(id=edge.target_node_id).first()
        if tgt:
            context["downstream"].append({"id": tgt.id, "type": tgt.node_type, "name": tgt.node_name or tgt.node_id})

    return context


@router.get("/{account_id}/nodes/{node_db_id}", response_model=TopologyNodeResponse)
def get_node_detail(account_id: int, node_db_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    verify_account_access(current_user, account_id, db)
    node = db.query(TopologyNode).filter_by(id=node_db_id, account_id=account_id).first()
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    meta = json.loads(node.metadata_json) if node.metadata_json else None
    return TopologyNodeResponse(
        id=f"{node.node_type}:{node.node_id}",
        label=node.node_name or node.node_id,
        node_type=node.node_type,
        region=node.region,
        metadata=meta,
    )


@router.get("/{account_id}/nodes/{node_db_id}/health", response_model=NodeHealthResponse)
def get_node_health(account_id: int, node_db_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    verify_account_access(current_user, account_id, db)
    node = db.query(TopologyNode).filter_by(id=node_db_id, account_id=account_id).first()
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")

    account = db.query(AWSAccount).filter_by(id=account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    from backend.config import settings
    from backend.aws.client_factory import AWSClientFactory
    factory = AWSClientFactory(settings.SECRET_KEY)

    health_status = "unknown"
    details = {}

    try:
        if node.node_type == "alb":
            client = factory.get_client(account, "elbv2", node.region)
            resp = client.describe_target_groups(LoadBalancerArn=node.node_id)
            healthy_count = 0
            total = 0
            for tg in resp.get("TargetGroups", []):
                health_resp = client.describe_target_health(TargetGroupArn=tg["TargetGroupArn"])
                for t in health_resp.get("TargetHealthDescriptions", []):
                    total += 1
                    if t.get("TargetHealth", {}).get("State") == "healthy":
                        healthy_count += 1
            health_status = "healthy" if healthy_count == total and total > 0 else "degraded"
            details = {"healthy_targets": healthy_count, "total_targets": total}

        elif node.node_type == "ecs_service":
            client = factory.get_client(account, "ecs", node.region)
            meta = json.loads(node.metadata_json) if node.metadata_json else {}
            cluster = meta.get("cluster_arn", "")
            if cluster:
                resp = client.describe_services(cluster=cluster, services=[node.node_id])
                if resp.get("services"):
                    svc = resp["services"][0]
                    desired = svc.get("desiredCount", 0)
                    running = svc.get("runningCount", 0)
                    health_status = "healthy" if running >= desired and desired > 0 else "degraded"
                    details = {"desired": desired, "running": running}

        elif node.node_type == "rds":
            client = factory.get_client(account, "rds", node.region)
            name = node.node_id.split(":")[-1] if ":" in node.node_id else node.node_id
            resp = client.describe_db_instances(DBInstanceIdentifier=name)
            if resp.get("DBInstances"):
                status = resp["DBInstances"][0]["DBInstanceStatus"]
                health_status = "healthy" if status == "available" else status
                details = {"db_status": status}

    except Exception as e:
        details = {"error": str(e)}

    return NodeHealthResponse(
        node_id=f"{node.node_type}:{node.node_id}",
        node_type=node.node_type,
        health_status=health_status,
        details=details,
    )


@router.get("/{account_id}/reverse-lookup", response_model=ReverseLookupResponse)
def reverse_lookup(
    account_id: int,
    domain: str = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    verify_account_access(current_user, account_id, db)

    start_node = db.query(TopologyNode).filter_by(
        account_id=account_id,
        node_type="route53",
        node_id=domain,
    ).first()

    if not start_node:
        start_node = db.query(TopologyNode).filter(
            TopologyNode.account_id == account_id,
            TopologyNode.node_type == "route53",
            TopologyNode.node_id.contains(domain),
        ).first()

    if not start_node:
        raise HTTPException(status_code=404, detail=f"Domain '{domain}' not found in topology")

    chain_nodes = []
    chain_edges = []
    visited = set()
    queue = [start_node.id]

    while queue:
        current_id = queue.pop(0)
        if current_id in visited:
            continue
        visited.add(current_id)

        node = db.query(TopologyNode).filter_by(id=current_id).first()
        if node:
            meta = json.loads(node.metadata_json) if node.metadata_json else None
            chain_nodes.append(TopologyNodeResponse(
                id=f"{node.node_type}:{node.node_id}",
                label=node.node_name or node.node_id,
                node_type=node.node_type,
                region=node.region,
                metadata=meta,
            ))

        downstream_edges = db.query(TopologyEdge).filter_by(source_node_id=current_id).all()
        for edge in downstream_edges:
            src_node = db.query(TopologyNode).filter_by(id=edge.source_node_id).first()
            tgt_node = db.query(TopologyNode).filter_by(id=edge.target_node_id).first()
            if src_node and tgt_node:
                chain_edges.append(TopologyEdgeResponse(
                    source=f"{src_node.node_type}:{src_node.node_id}",
                    target=f"{tgt_node.node_type}:{tgt_node.node_id}",
                    edge_type=edge.edge_type,
                ))
            if edge.target_node_id not in visited:
                queue.append(edge.target_node_id)

    return ReverseLookupResponse(domain=domain, chain=chain_nodes, edges=chain_edges)


@router.get("/{account_id}/nodes/{node_db_id}/context")
def get_node_context(account_id: int, node_db_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Auto-resolve all metric/log parameters from node context. Frontend needs zero manual input."""
    verify_account_access(current_user, account_id, db)
    node = db.query(TopologyNode).filter_by(id=node_db_id, account_id=account_id).first()
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")

    meta = json.loads(node.metadata_json) if node.metadata_json else {}

    context = {
        "node_id": node.id,
        "node_type": node.node_type,
        "node_name": node.node_name or node.node_id,
        "resource_id": node.node_id,
        "region": node.region,
        "account_id": account_id,
        "metrics": _resolve_metrics(node, meta),
        "log_groups": _resolve_log_groups(node, meta, db, account_id),
        "console_url": _resolve_console_url(node, meta),
        "upstream": [],
        "downstream": [],
    }

    upstream_edges = db.query(TopologyEdge).filter_by(target_node_id=node.id).all()
    for edge in upstream_edges:
        src = db.query(TopologyNode).filter_by(id=edge.source_node_id).first()
        if src:
            context["upstream"].append({
                "id": src.id,
                "type": src.node_type,
                "name": src.node_name or src.node_id,
            })

    downstream_edges = db.query(TopologyEdge).filter_by(source_node_id=node.id).all()
    for edge in downstream_edges:
        tgt = db.query(TopologyNode).filter_by(id=edge.target_node_id).first()
        if tgt:
            context["downstream"].append({
                "id": tgt.id,
                "type": tgt.node_type,
                "name": tgt.node_name or tgt.node_id,
            })

    return context


def _resolve_metrics(node: TopologyNode, meta: dict) -> list[dict]:
    """Return pre-configured metric descriptors for this node type."""
    node_id = node.node_id

    if node.node_type == "alb":
        arn_suffix = node_id.split("loadbalancer/")[-1] if "loadbalancer/" in node_id else node_id
        dims = [{"Name": "LoadBalancer", "Value": arn_suffix}]
        return [
            {"key": "alb_5xx", "label": "5xx 错误数", "dimensions": dims},
            {"key": "alb_requests", "label": "请求总量", "dimensions": dims},
        ]

    elif node.node_type == "ecs_service":
        parts = node_id.split("/")
        cluster_name = meta.get("cluster_arn", "").split("/")[-1] if meta.get("cluster_arn") else (parts[-2] if len(parts) >= 3 else "")
        service_name = parts[-1] if parts else node_id
        dims = [
            {"Name": "ClusterName", "Value": cluster_name},
            {"Name": "ServiceName", "Value": service_name},
        ]
        return [
            {"key": "ecs_cpu", "label": "CPU 使用率", "dimensions": dims},
            {"key": "ecs_memory", "label": "内存使用率", "dimensions": dims},
        ]

    elif node.node_type == "rds":
        db_id = node_id.split(":")[-1] if ":" in node_id else node_id
        dims = [{"Name": "DBInstanceIdentifier", "Value": db_id}]
        return [
            {"key": "rds_connections", "label": "连接数", "dimensions": dims},
            {"key": "rds_cpu", "label": "CPU 使用率", "dimensions": dims},
        ]

    elif node.node_type == "elasticache":
        cluster_id = node_id.split(":")[-1] if ":" in node_id else node_id
        dims = [{"Name": "CacheClusterId", "Value": cluster_id}]
        return [
            {"key": "cache_hit_rate", "label": "缓存命中率", "dimensions": dims},
            {"key": "cache_connections", "label": "当前连接数", "dimensions": dims},
        ]

    elif node.node_type == "ec2":
        dims = [{"Name": "InstanceId", "Value": node_id}]
        return [
            {"key": "ec2_cpu", "label": "CPU 使用率", "dimensions": dims},
        ]

    return []


def _resolve_log_groups(node: TopologyNode, meta: dict, db: Session, account_id: int) -> list[dict]:
    """Discover actual log groups from the environment — no pattern guessing."""
    if node.node_type == "ecs_service":
        resource = db.query(Resource).filter_by(
            account_id=account_id,
            resource_type="ecs_service",
            resource_id=node.node_id,
        ).first()
        if not resource:
            return []
        res_meta = json.loads(resource.metadata_json) if resource.metadata_json else {}
        task_def_arn = res_meta.get("task_definition")
        if not task_def_arn:
            return []
        try:
            from backend.config import settings
            from backend.aws.client_factory import AWSClientFactory
            from backend.aws.topology_fetcher import fetch_ecs_log_groups

            account = db.query(AWSAccount).filter_by(id=account_id).first()
            if not account:
                return []
            factory = AWSClientFactory(settings.SECRET_KEY)
            log_groups = fetch_ecs_log_groups(factory, account, task_def_arn, node.region)
            return [
                {"name": lg["name"], "label": f"{lg['container']}: {lg['name']}" if lg.get("container") else lg["name"]}
                for lg in log_groups
            ]
        except Exception as e:
            logger.warning(f"Failed to discover log groups for {node.node_id}: {e}")
            return []

    elif node.node_type == "rds":
        db_id = node.node_id.split(":")[-1] if ":" in node.node_id else node.node_id
        return [
            {"name": f"/aws/rds/instance/{db_id}/slowquery", "label": f"RDS 慢查询: {db_id}"},
            {"name": f"/aws/rds/instance/{db_id}/error", "label": f"RDS 错误日志: {db_id}"},
        ]

    elif node.node_type == "alb":
        alb_name = meta.get("name") or node.node_name or ""
        return [
            {"name": f"/aws/elasticloadbalancing/{alb_name}", "label": f"ALB 访问日志: {alb_name}"},
        ]

    return []


def _resolve_console_url(node: TopologyNode, meta: dict) -> str:
    region = node.region
    base = f"https://{region}.console.aws.amazon.com"
    node_id = node.node_id

    if node.node_type == "alb":
        return f"{base}/ec2/home?region={region}#LoadBalancer:loadBalancerArn={node_id}"
    elif node.node_type == "ecs_service":
        parts = node_id.split("/")
        cluster = parts[-2] if len(parts) >= 3 else ""
        service = parts[-1] if parts else node_id
        return f"{base}/ecs/home?region={region}#/clusters/{cluster}/services/{service}"
    elif node.node_type == "rds":
        db_id = node_id.split(":")[-1] if ":" in node_id else node_id
        return f"{base}/rds/home?region={region}#database:id={db_id}"
    elif node.node_type == "ec2":
        return f"{base}/ec2/home?region={region}#InstanceDetails:instanceId={node_id}"
    elif node.node_type == "elasticache":
        cluster_id = node_id.split(":")[-1] if ":" in node_id else node_id
        return f"{base}/elasticache/home?region={region}#/redis/{cluster_id}"
    elif node.node_type == "route53":
        return f"{base}/route53/v2/hostedzones"
    return f"{base}/cloudwatch/home?region={region}"
