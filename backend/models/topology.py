from datetime import datetime, timezone

from sqlalchemy import String, DateTime, Integer, Text, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from backend.database import Base


class TopologyNode(Base):
    __tablename__ = "topology_nodes"
    __table_args__ = (UniqueConstraint("account_id", "node_type", "node_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    account_id: Mapped[int] = mapped_column(Integer, ForeignKey("aws_accounts.id"), nullable=False)
    node_type: Mapped[str] = mapped_column(String(32), nullable=False)
    node_id: Mapped[str] = mapped_column(String(256), nullable=False)
    node_name: Mapped[str | None] = mapped_column(String(256), nullable=True)
    region: Mapped[str] = mapped_column(String(32), nullable=False)
    metadata_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_synced_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))


class TopologyEdge(Base):
    __tablename__ = "topology_edges"
    __table_args__ = (UniqueConstraint("source_node_id", "target_node_id", "edge_type"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    account_id: Mapped[int] = mapped_column(Integer, ForeignKey("aws_accounts.id"), nullable=False)
    source_node_id: Mapped[int] = mapped_column(Integer, ForeignKey("topology_nodes.id"), nullable=False)
    target_node_id: Mapped[int] = mapped_column(Integer, ForeignKey("topology_nodes.id"), nullable=False)
    edge_type: Mapped[str] = mapped_column(String(32), nullable=False)
    metadata_json: Mapped[str | None] = mapped_column(Text, nullable=True)
