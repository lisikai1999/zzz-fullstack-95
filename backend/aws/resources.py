import logging

from backend.aws.client_factory import AWSClientFactory
from backend.models.aws_account import AWSAccount

logger = logging.getLogger(__name__)

COMMON_REGIONS = [
    "us-east-1", "us-east-2", "us-west-1", "us-west-2",
    "eu-west-1", "eu-west-2", "eu-central-1",
    "ap-southeast-1", "ap-northeast-1",
]


def fetch_ec2_instances(factory: AWSClientFactory, account: AWSAccount, regions: list[str] | None = None) -> list[dict]:
    results = []
    for region in (regions or COMMON_REGIONS):
        try:
            client = factory.get_client(account, "ec2", region)
            paginator = client.get_paginator("describe_instances")
            for page in paginator.paginate():
                for reservation in page["Reservations"]:
                    for instance in reservation["Instances"]:
                        if instance["State"]["Name"] == "terminated":
                            continue
                        name = ""
                        tags = instance.get("Tags", [])
                        for tag in tags:
                            if tag["Key"] == "Name":
                                name = tag["Value"]
                                break
                        results.append({
                            "resource_type": "ec2_instance",
                            "resource_id": instance["InstanceId"],
                            "resource_name": name,
                            "region": region,
                            "tags": tags,
                            "status": instance["State"]["Name"],
                            "metadata": {
                                "instance_type": instance.get("InstanceType"),
                                "private_ip": instance.get("PrivateIpAddress"),
                                "public_ip": instance.get("PublicIpAddress"),
                                "vpc_id": instance.get("VpcId"),
                                "subnet_id": instance.get("SubnetId"),
                                "launch_time": str(instance.get("LaunchTime", "")),
                            },
                        })
        except Exception as e:
            logger.warning(f"EC2 fetch failed in {region}: {e}")
    return results


def fetch_rds_instances(factory: AWSClientFactory, account: AWSAccount, regions: list[str] | None = None) -> list[dict]:
    results = []
    for region in (regions or COMMON_REGIONS):
        try:
            client = factory.get_client(account, "rds", region)
            paginator = client.get_paginator("describe_db_instances")
            for page in paginator.paginate():
                for db in page["DBInstances"]:
                    results.append({
                        "resource_type": "rds_instance",
                        "resource_id": db["DBInstanceArn"],
                        "resource_name": db["DBInstanceIdentifier"],
                        "region": region,
                        "tags": db.get("TagList", []),
                        "status": db["DBInstanceStatus"],
                        "metadata": {
                            "engine": db.get("Engine"),
                            "engine_version": db.get("EngineVersion"),
                            "instance_class": db.get("DBInstanceClass"),
                            "endpoint": db.get("Endpoint", {}).get("Address"),
                            "port": db.get("Endpoint", {}).get("Port"),
                            "multi_az": db.get("MultiAZ"),
                            "storage_gb": db.get("AllocatedStorage"),
                        },
                    })
        except Exception as e:
            logger.warning(f"RDS fetch failed in {region}: {e}")
    return results


def fetch_ecs_services(factory: AWSClientFactory, account: AWSAccount, regions: list[str] | None = None) -> list[dict]:
    results = []
    for region in (regions or COMMON_REGIONS):
        try:
            client = factory.get_client(account, "ecs", region)

            cluster_arns = []
            clusters_paginator = client.get_paginator("list_clusters")
            for page in clusters_paginator.paginate():
                cluster_arns.extend(page.get("clusterArns", []))

            for cluster_arn in cluster_arns:
                service_arns = []
                services_paginator = client.get_paginator("list_services")
                for page in services_paginator.paginate(cluster=cluster_arn):
                    service_arns.extend(page.get("serviceArns", []))

                if not service_arns:
                    continue

                for i in range(0, len(service_arns), 10):
                    batch = service_arns[i:i + 10]
                    desc = client.describe_services(cluster=cluster_arn, services=batch)
                    for svc in desc.get("services", []):
                        results.append({
                            "resource_type": "ecs_service",
                            "resource_id": svc["serviceArn"],
                            "resource_name": svc["serviceName"],
                            "region": region,
                            "tags": svc.get("tags", []),
                            "status": svc.get("status"),
                            "metadata": {
                                "cluster_arn": cluster_arn,
                                "task_definition": svc.get("taskDefinition"),
                                "desired_count": svc.get("desiredCount"),
                                "running_count": svc.get("runningCount"),
                                "launch_type": svc.get("launchType"),
                            },
                        })
        except Exception as e:
            logger.warning(f"ECS fetch failed in {region}: {e}")
    return results


def fetch_albs(factory: AWSClientFactory, account: AWSAccount, regions: list[str] | None = None) -> list[dict]:
    results = []
    for region in (regions or COMMON_REGIONS):
        try:
            client = factory.get_client(account, "elbv2", region)
            paginator = client.get_paginator("describe_load_balancers")
            for page in paginator.paginate():
                for lb in page["LoadBalancers"]:
                    if lb["Type"] != "application":
                        continue
                    tags = []
                    try:
                        tags_resp = client.describe_tags(ResourceArns=[lb["LoadBalancerArn"]])
                        if tags_resp.get("TagDescriptions"):
                            tags = tags_resp["TagDescriptions"][0].get("Tags", [])
                    except Exception:
                        pass
                    results.append({
                        "resource_type": "alb",
                        "resource_id": lb["LoadBalancerArn"],
                        "resource_name": lb.get("LoadBalancerName", ""),
                        "region": region,
                        "tags": tags,
                        "status": lb.get("State", {}).get("Code", "active"),
                        "metadata": {
                            "dns_name": lb.get("DNSName"),
                            "scheme": lb.get("Scheme"),
                            "vpc_id": lb.get("VpcId"),
                            "availability_zones": [az["ZoneName"] for az in lb.get("AvailabilityZones", [])],
                        },
                    })
        except Exception as e:
            logger.warning(f"ALB fetch failed in {region}: {e}")
    return results


def fetch_elasticache_clusters(factory: AWSClientFactory, account: AWSAccount, regions: list[str] | None = None) -> list[dict]:
    results = []
    for region in (regions or COMMON_REGIONS):
        try:
            client = factory.get_client(account, "elasticache", region)
            paginator = client.get_paginator("describe_cache_clusters")
            for page in paginator.paginate(ShowCacheNodeInfo=True):
                for cluster in page["CacheClusters"]:
                    endpoint = ""
                    if cluster.get("ConfigurationEndpoint"):
                        endpoint = cluster["ConfigurationEndpoint"].get("Address", "")
                    elif cluster.get("CacheNodes"):
                        endpoint = cluster["CacheNodes"][0].get("Endpoint", {}).get("Address", "")
                    tags = []
                    arn = cluster.get("ARN", "")
                    if arn:
                        try:
                            tags_resp = client.list_tags_for_resource(ResourceName=arn)
                            tags = tags_resp.get("TagList", [])
                        except Exception:
                            pass
                    results.append({
                        "resource_type": "elasticache_cluster",
                        "resource_id": arn or cluster["CacheClusterId"],
                        "resource_name": cluster["CacheClusterId"],
                        "region": region,
                        "tags": tags,
                        "status": cluster.get("CacheClusterStatus"),
                        "metadata": {
                            "engine": cluster.get("Engine"),
                            "engine_version": cluster.get("EngineVersion"),
                            "node_type": cluster.get("CacheNodeType"),
                            "num_nodes": cluster.get("NumCacheNodes"),
                            "endpoint": endpoint,
                        },
                    })
        except Exception as e:
            logger.warning(f"ElastiCache fetch failed in {region}: {e}")
    return results
