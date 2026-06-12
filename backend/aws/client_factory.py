import boto3

from backend.core.encryption import decrypt_value
from backend.models.aws_account import AWSAccount


class AWSClientFactory:
    def __init__(self, secret_key: str):
        self._secret_key = secret_key

    def get_client(self, account: AWSAccount, service: str, region: str | None = None):
        ak = decrypt_value(account.access_key_encrypted, self._secret_key)
        sk = decrypt_value(account.secret_key_encrypted, self._secret_key)
        session = boto3.Session(
            aws_access_key_id=ak,
            aws_secret_access_key=sk,
            region_name=region or account.default_region,
        )
        return session.client(service)

    def get_multi_region_clients(self, account: AWSAccount, service: str, regions: list[str]) -> dict:
        return {r: self.get_client(account, service, r) for r in regions}
