from pydantic import BaseModel


class ResourceResponse(BaseModel):
    id: int
    account_id: int
    resource_type: str
    resource_id: str
    resource_name: str | None = None
    region: str
    tags: str | None = None
    metadata_json: str | None = None
    status: str | None = None
    is_idle: bool
    is_untagged: bool

    class Config:
        from_attributes = True


class ResourceSummary(BaseModel):
    resource_type: str
    count: int
    idle_count: int
    untagged_count: int
