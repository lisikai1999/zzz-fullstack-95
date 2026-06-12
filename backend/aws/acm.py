from backend.aws.client_factory import AWSClientFactory
from backend.models.aws_account import AWSAccount

COMMON_REGIONS = [
    "us-east-1", "us-east-2", "us-west-1", "us-west-2",
    "eu-west-1", "eu-west-2", "eu-central-1",
    "ap-southeast-1", "ap-northeast-1",
]


def fetch_acm_certificates(factory: AWSClientFactory, account: AWSAccount, regions: list[str] | None = None) -> list[dict]:
    results = []
    for region in (regions or COMMON_REGIONS):
        client = factory.get_client(account, "acm", region)
        paginator = client.get_paginator("list_certificates")
        for page in paginator.paginate():
            for cert_summary in page["CertificateSummaryList"]:
                arn = cert_summary["CertificateArn"]
                detail = client.describe_certificate(CertificateArn=arn)["Certificate"]
                results.append({
                    "certificate_arn": arn,
                    "domain_name": detail.get("DomainName", ""),
                    "san_names": detail.get("SubjectAlternativeNames", []),
                    "status": detail.get("Status", ""),
                    "issuer": detail.get("Issuer"),
                    "not_before": detail.get("NotBefore"),
                    "not_after": detail.get("NotAfter"),
                    "in_use_by": detail.get("InUseBy", []),
                    "region": region,
                })
    return results
