import json
import re
import logging
from datetime import datetime, timezone

from backend.config import settings
from backend.database import SessionLocal
from backend.aws.client_factory import AWSClientFactory
from backend.aws.topology_fetcher import (
    fetch_route53_records,
    fetch_alb_details,
    fetch_target_groups_for_alb,
    fetch_ecs_task_definitions_env,
    build_ecs_ip_to_service_map,
    fetch_ecs_log_groups,
)
from backend.models.aws_account import AWSAccount
from backend.models.topology import TopologyNode, TopologyEdge
from backend.models.resource import Resource
from backend.models.sync_log import SyncLog

logger = logging.getLogger(__name__)

RDS_ENDPOINT_PATTERN = re.compile(r"[\w-]+\.[\w-]+\.[\w-]+\.rds\.amazonaws\.com")
ELASTICACHE_ENDPOINT_PATTERN = re.compile(r"[\w-]+\.[\w-]+\.cache\.amazonaws\.com")


def sync_all_topologies():
    db = SessionLocal()
    try:
        accounts = db.query(AWSAccount).filter(AWSAccount.is_active == True).all()
        for account in accounts:
            _sync_account_topology(account, db)
    except Exception as e:
        logger.error(f"Topology sync error: {e}")
    finally:
        db.close()


def _sync_account_topology(account: AWSAccount, db):
    log = SyncLog(account_id=account.id, job_type="topology", status="running")
    db.add(log)
    db.commit()

    try:
        factory = AWSClientFactory(settings.SECRET_KEY)
        now = datetime.now(timezone.utc)

        db.query(TopologyEdge).filter_by(account_id=account.id).delete()
        db.query(TopologyNode).filter_by(account_id=account.id).delete()
        db.flush()

        route53_records = fetch_route53_records(factory, account)
        albs = fetch_alb_details(factory, account)
        alb_dns_map = {alb["dns_name"].lower(): alb for alb in albs}

        nodes = {}
        edges = []

        for record in route53_records:
            node_id = f"route53:{record['name']}"
            nodes[node_id] = TopologyNode(
                account_id=account.id,
                node_type="route53",
                node_id=record["name"],
                node_name=record["name"],
                region="global",
                metadata_json=json.dumps({"type": record["type"], "zone": record["zone_name"]}),
                last_synced_at=now,
            )

        for alb in albs:
            node_id = f"alb:{alb['arn']}"
            nodes[node_id] = TopologyNode(
                account_id=account.id,
                node_type="alb",
                node_id=alb["arn"],
                node_name=alb["name"],
                region=alb["region"],
                metadata_json=json.dumps({"dns_name": alb["dns_name"], "scheme": alb["scheme"]}),
                last_synced_at=now,
            )

        for record in route53_records:
            target = record.get("alias_target") or ""
            if not target:
                for val in record.get("values", []):
                    if val.lower().rstrip(".") in alb_dns_map:
                        target = val.lower().rstrip(".")
                        break
            target_lower = target.lower().rstrip(".")
            if target_lower in alb_dns_map:
                matched_alb = alb_dns_map[target_lower]
                edges.append(("route53:" + record["name"], "alb:" + matched_alb["arn"], "dns_to_alb"))

        # Build IP→service maps per region (for proper ECS target resolution)
        ip_service_maps: dict[str, dict[str, str]] = {}

        for alb in albs:
            region = alb["region"]
            if region not in ip_service_maps:
                try:
                    ip_service_maps[region] = build_ecs_ip_to_service_map(factory, account, region)
                except Exception as e:
                    logger.warning(f"Failed to build ECS IP map for {region}: {e}")
                    ip_service_maps[region] = {}

            tgs = fetch_target_groups_for_alb(factory, account, alb["arn"], region)
            for tg in tgs:
                tg_node_id = f"target_group:{tg['arn']}"
                nodes[tg_node_id] = TopologyNode(
                    account_id=account.id,
                    node_type="target_group",
                    node_id=tg["arn"],
                    node_name=tg["name"],
                    region=region,
                    metadata_json=json.dumps({"target_type": tg["target_type"], "port": tg["port"]}),
                    last_synced_at=now,
                )
                edges.append(("alb:" + alb["arn"], tg_node_id, "alb_to_tg"))

                linked_services = set()
                for target in tg.get("targets", []):
                    target_id = target["id"]
                    if target_id.startswith("i-"):
                        instance_node_id = f"ec2:{target_id}"
                        if instance_node_id not in nodes:
                            nodes[instance_node_id] = TopologyNode(
                                account_id=account.id,
                                node_type="ec2",
                                node_id=target_id,
                                node_name=target_id,
                                region=region,
                                metadata_json=json.dumps({"health": target.get("health_state")}),
                                last_synced_at=now,
                            )
                        edges.append((tg_node_id, instance_node_id, "tg_to_instance"))
                    elif tg["target_type"] == "ip":
                        # Look up the actual ECS service that owns this IP
                        svc_arn = ip_service_maps.get(region, {}).get(target_id)
                        if svc_arn and svc_arn not in linked_services:
                            linked_services.add(svc_arn)
                            svc_node_id = f"ecs_service:{svc_arn}"
                            if svc_node_id not in nodes:
                                nodes[svc_node_id] = TopologyNode(
                                    account_id=account.id,
                                    node_type="ecs_service",
                                    node_id=svc_arn,
                                    node_name=svc_arn.split("/")[-1],
                                    region=region,
                                    metadata_json=json.dumps({"cluster_arn": "/".join(svc_arn.split("/")[:-1])}),
                                    last_synced_at=now,
                                )
                            edges.append((tg_node_id, svc_node_id, "tg_to_ecs"))

        _discover_backend_deps(factory, account, nodes, edges, db, now)

        for node in nodes.values():
            db.add(node)
        db.flush()

        node_db_map = {}
        for n in db.query(TopologyNode).filter_by(account_id=account.id).all():
            key = f"{n.node_type}:{n.node_id}"
            node_db_map[key] = n.id

        for src_key, tgt_key, edge_type in edges:
            src_id = node_db_map.get(src_key)
            tgt_id = node_db_map.get(tgt_key)
            if src_id and tgt_id:
                db.add(TopologyEdge(
                    account_id=account.id,
                    source_node_id=src_id,
                    target_node_id=tgt_id,
                    edge_type=edge_type,
                ))

        log.status = "success"
        log.finished_at = now
        log.items_synced = len(nodes)
        db.commit()

    except Exception as e:
        db.rollback()
        log.status = "failed"
        log.finished_at = datetime.now(timezone.utc)
        log.error_message = str(e)
        db.add(log)
        db.commit()
        logger.error(f"Topology sync failed for account {account.account_id}: {e}")


def _discover_backend_deps(factory, account, nodes, edges, db, now):
    ecs_nodes = {k: v for k, v in nodes.items() if v.node_type == "ecs_service"}

    rds_resources = db.query(Resource).filter_by(
        account_id=account.id,
        resource_type="rds_instance",
    ).all()
    cache_resources = db.query(Resource).filter_by(
        account_id=account.id,
        resource_type="elasticache_cluster",
    ).all()

    rds_endpoint_map = {}
    for r in rds_resources:
        meta = json.loads(r.metadata_json) if r.metadata_json else {}
        ep = meta.get("endpoint", "")
        if ep:
            rds_endpoint_map[ep.lower()] = r

    cache_endpoint_map = {}
    for r in cache_resources:
        meta = json.loads(r.metadata_json) if r.metadata_json else {}
        ep = meta.get("endpoint", "")
        if ep:
            cache_endpoint_map[ep.lower()] = r

    for node_key, node in list(ecs_nodes.items()):
        try:
            svc_resource = db.query(Resource).filter_by(
                account_id=account.id,
                resource_type="ecs_service",
                resource_id=node.node_id,
            ).first()
            if not svc_resource:
                continue
            meta = json.loads(svc_resource.metadata_json) if svc_resource.metadata_json else {}
            task_def = meta.get("task_definition")
            if not task_def:
                continue

            env_vars = fetch_ecs_task_definitions_env(factory, account, task_def, node.region)
            for env in env_vars:
                val = env.get("value", "")
                rds_match = RDS_ENDPOINT_PATTERN.search(val)
                if rds_match:
                    ep = rds_match.group(0).lower()
                    rds_res = rds_endpoint_map.get(ep)
                    if rds_res:
                        rds_node_id = f"rds:{rds_res.resource_id}"
                        if rds_node_id not in nodes:
                            nodes[rds_node_id] = TopologyNode(
                                account_id=account.id,
                                node_type="rds",
                                node_id=rds_res.resource_id,
                                node_name=rds_res.resource_name,
                                region=rds_res.region,
                                metadata_json=rds_res.metadata_json,
                                last_synced_at=now,
                            )
                        edges.append((node_key, rds_node_id, "app_to_db"))

                cache_match = ELASTICACHE_ENDPOINT_PATTERN.search(val)
                if cache_match:
                    ep = cache_match.group(0).lower()
                    cache_res = cache_endpoint_map.get(ep)
                    if cache_res:
                        cache_node_id = f"elasticache:{cache_res.resource_id}"
                        if cache_node_id not in nodes:
                            nodes[cache_node_id] = TopologyNode(
                                account_id=account.id,
                                node_type="elasticache",
                                node_id=cache_res.resource_id,
                                node_name=cache_res.resource_name,
                                region=cache_res.region,
                                metadata_json=cache_res.metadata_json,
                                last_synced_at=now,
                            )
                        edges.append((node_key, cache_node_id, "app_to_cache"))
        except Exception as e:
            logger.warning(f"Failed to discover deps for {node_key}: {e}")
