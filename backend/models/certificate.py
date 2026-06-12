from datetime import datetime, timezone

from sqlalchemy import String, Boolean, DateTime, Integer, Text, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from backend.database import Base


class Certificate(Base):
    __tablename__ = "certificates"
    __table_args__ = (UniqueConstraint("account_id", "certificate_arn"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    account_id: Mapped[int] = mapped_column(Integer, ForeignKey("aws_accounts.id"), nullable=False)
    certificate_arn: Mapped[str] = mapped_column(String(512), nullable=False)
    domain_name: Mapped[str] = mapped_column(String(256), nullable=False)
    san_names: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    issuer: Mapped[str | None] = mapped_column(String(128), nullable=True)
    not_before: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    not_after: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    in_use_by: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_orphan: Mapped[bool] = mapped_column(Boolean, default=False)
    alert_level: Mapped[str | None] = mapped_column(String(16), nullable=True)
    region: Mapped[str] = mapped_column(String(32), nullable=False)
    last_synced_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
