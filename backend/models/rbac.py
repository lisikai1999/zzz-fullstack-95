from sqlalchemy import Integer, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from backend.database import Base


class UserAccountAccess(Base):
    __tablename__ = "user_account_access"
    __table_args__ = (UniqueConstraint("user_id", "account_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    account_id: Mapped[int] = mapped_column(Integer, ForeignKey("aws_accounts.id"), nullable=False)
