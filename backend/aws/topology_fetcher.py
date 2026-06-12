from backend.aws.client_factory import AWSClientFactory
from backend.models.aws_account import AWSAccount

COMMON_REGIONS = [
    "us-east-1", "us-east-2", "us-west-1", "us-west-2",
    "eu-west-1", "eu-west-2", "eu-central-1",
    "ap-southeast-1", "ap-northeast-1",
]


def fetch_route53_records(factory: AWSClientFactory, account: AWSAccount) -> list[dict]:
    client = factory.get_client(account, "route53", "us-east-1")
    zones_resp = client.list_hosted_zones()
    results = []
    for zone in zones_resp.get("HostedZones", []):
        zone_id = zone["Id"].split("/")[-1]
        paginator = client.get_paginator("list_resource_record_sets")
        for page in paginator.paginate(HostedZoneId=zone_id):
            for record in page["ResourceRecordSets"]:
                if record["Type"] not in ("A", "AAAA", "CNAME"):
                    continue
                alias_target = None
                if record.get("AliasTarget"):
                    alias_target = record["AliasTarget"].get("DNSName", "").rstrip(".")
                results.append({
                    "zone_id": zone_id,
                    "zone_name": zone["Name"].rstrip("."),
                    "name": record["Name"].rstrip("."),
                    "type": record["Type"],
                    "alias_target": alias_target,
                    "values": [rr["Value"] for rr in record.get("ResourceRecords", [])],
                })
    return results


def fetch_alb_details(factory: AWSClientFactory, account: AWSAccount, regions: list[str] | None = None) -> list[dict]:
    results = []
    for region in (regions or COMMON_REGIONS):
        client = factory.get_client(account, "elbv2", region)
        paginator = client.get_paginator("describe_load_balancers")
        for page in paginator.paginate():
            for lb in page["LoadBalancers"]:
                if lb["Type"] != "application":
                    continue
                results.append({
                    "arn": lb["LoadBalancerArn"],
                    "name": lb["LoadBalancerName"],
                    "dns_name": lb["DNSName"],
                    "region": region,
                    "vpc_id": lb.get("VpcId"),
                    "scheme": lb.get("Scheme"),
                })
    return results


def fetch_target_groups_for_alb(factory: AWSClientFactory, account: AWSAccount, alb_arn: str, region: str) -> list[dict]:
    client = factory.get_client(account, "elbv2", region)
    listeners = client.describe_listeners(LoadBalancerArn=alb_arn).get("Listeners", [])
    tg_arns = set()
    for listener in listeners:
        rules = client.describe_rules(ListenerArn=listener["ListenerArn"]).get("Rules", [])
        for rule in rules:
            for action in rule.get("Actions", []):
                if action.get("TargetGroupArn"):
                    tg_arns.add(action["TargetGroupArn"])
                for tg in action.get("ForwardConfig", {}).get("TargetGroups", []):
                    tg_arns.add(tg["TargetGroupArn"])

    results = []
    if tg_arns:
        tgs = client.describe_target_groups(TargetGroupArns=list(tg_arns)).get("TargetGroups", [])
        for tg in tgs:
            health = client.describe_target_health(TargetGroupArn=tg["TargetGroupArn"])
            targets = []
            for th in health.get("TargetHealthDescriptions", []):
                targets.append({
                    "id": th["Target"]["Id"],
                    "port": th["Target"].get("Port"),
                    "health_state": th.get("TargetHealth", {}).get("State"),
                })
            results.append({
                "arn": tg["TargetGroupArn"],
                "name": tg["TargetGroupName"],
                "target_type": tg.get("TargetType"),
                "port": tg.get("Port"),
                "protocol": tg.get("Protocol"),
                "targets": targets,
            })
    return results


def fetch_ecs_task_definitions_env(factory: AWSClientFactory, account: AWSAccount, task_def_arn: str, region: str) -> list[dict]:
    client = factory.get_client(account, "ecs", region)
    resp = client.describe_task_definition(taskDefinition=task_def_arn)
    env_vars = []
    for container in resp.get("taskDefinition", {}).get("containerDefinitions", []):
        for env in container.get("environment", []):
            env_vars.append({"name": env["Name"], "value": env["Value"]})
    return env_vars


def build_ecs_ip_to_service_map(factory: AWSClientFactory, account: AWSAccount, region: str) -> dict[str, str]:
    """Build a mapping of task private IP → service ARN by listing all running tasks in the region."""
    client = factory.get_client(account, "ecs", region)
    ip_map: dict[str, str] = {}

    cluster_arns = []
    clusters_paginator = client.get_paginator("list_clusters")
    for page in clusters_paginator.paginate():
        cluster_arns.extend(page.get("clusterArns", []))

    for cluster_arn in cluster_arns:
        service_arns = []
        svc_paginator = client.get_paginator("list_services")
        for page in svc_paginator.paginate(cluster=cluster_arn):
            service_arns.extend(page.get("serviceArns", []))

        for svc_arn in service_arns:
            task_arns = []
            task_paginator = client.get_paginator("list_tasks")
            for page in task_paginator.paginate(cluster=cluster_arn, serviceName=svc_arn):
                task_arns.extend(page.get("taskArns", []))

            if not task_arns:
                continue

            for i in range(0, len(task_arns), 100):
                batch = task_arns[i:i + 100]
                tasks_resp = client.describe_tasks(cluster=cluster_arn, tasks=batch)
                for task in tasks_resp.get("tasks", []):
                    for attachment in task.get("attachments", []):
                        if attachment.get("type") == "ElasticNetworkInterface":
                            for detail in attachment.get("details", []):
                                if detail.get("name") == "privateIPv4Address":
                                    ip_map[detail["value"]] = svc_arn
                    for container in task.get("containers", []):
                        for ni in container.get("networkInterfaces", []):
                            private_ip = ni.get("privateIpv4Address")
                            if private_ip:
                                ip_map[private_ip] = svc_arn

    return ip_map


def fetch_ecs_log_groups(factory: AWSClientFactory, account: AWSAccount, task_def_arn: str, region: str) -> list[dict]:
    """Extract actual log groups from task definition's container logConfiguration."""
    client = factory.get_client(account, "ecs", region)
    resp = client.describe_task_definition(taskDefinition=task_def_arn)
    log_groups = []
    seen = set()
    for container in resp.get("taskDefinition", {}).get("containerDefinitions", []):
        log_config = container.get("logConfiguration", {})
        if log_config.get("logDriver") == "awslogs":
            options = log_config.get("options", {})
            group = options.get("awslogs-group", "")
            if group and group not in seen:
                seen.add(group)
                log_groups.append({
                    "name": group,
                    "region": options.get("awslogs-region", region),
                    "container": container.get("name", ""),
                })
    return log_groups
