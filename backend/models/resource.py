from datetime import datetime, timezone

from sqlalchemy import String, Boolean, DateTime, Integer, Text, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from backend.database import Base


class Resource(Base):
    __tablename__ = "resources"
    __table_args__ = (UniqueConstraint("account_id", "resource_type", "resource_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    account_id: Mapped[int] = mapped_column(Integer, ForeignKey("aws_accounts.id"), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(64), nullable=False)
    resource_id: Mapped[str] = mapped_column(String(256), nullable=False)
    resource_name: Mapped[str | None] = mapped_column(String(256), nullable=True)
    region: Mapped[str] = mapped_column(String(32), nullable=False)
    tags: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    is_idle: Mapped[bool] = mapped_column(Boolean, default=False)
    is_untagged: Mapped[bool] = mapped_column(Boolean, default=False)
    last_synced_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
