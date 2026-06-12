from pydantic import BaseModel


class AWSAccountCreate(BaseModel):
    account_id: str
    account_name: str
    access_key: str
    secret_key: str
    default_region: str = "us-east-1"


class AWSAccountUpdate(BaseModel):
    account_name: str | None = None
    access_key: str | None = None
    secret_key: str | None = None
    default_region: str | None = None
    is_active: bool | None = None


class AWSAccountResponse(BaseModel):
    id: int
    account_id: str
    account_name: str
    default_region: str
    is_active: bool
    last_sync_at: str | None = None

    class Config:
        from_attributes = True


class AccountAccessUpdate(BaseModel):
    account_ids: list[int]
