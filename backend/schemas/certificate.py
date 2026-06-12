from pydantic import BaseModel


class CertificateResponse(BaseModel):
    id: int
    account_id: int
    certificate_arn: str
    domain_name: str
    san_names: str | None = None
    status: str
    not_before: str | None = None
    not_after: str
    in_use_by: str | None = None
    is_orphan: bool
    alert_level: str | None = None
    region: str

    class Config:
        from_attributes = True


class CertAlertSummary(BaseModel):
    critical: list[CertificateResponse]
    warning: list[CertificateResponse]
    info: list[CertificateResponse]
