from datetime import datetime, timezone

from sqlalchemy import String, Boolean, DateTime, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.database import Base


class AWSAccount(Base):
    __tablename__ = "aws_accounts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    account_id: Mapped[str] = mapped_column(String(12), unique=True, nullable=False)
    account_name: Mapped[str] = mapped_column(String(128), nullable=False)
    access_key_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    secret_key_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    default_region: Mapped[str] = mapped_column(String(32), default="us-east-1")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_sync_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
