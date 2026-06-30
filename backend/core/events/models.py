from typing import List

from sqlalchemy import DateTime, ForeignKey, JSON, String, func
from sqlalchemy.orm import Mapped, mapped_column

from core.db.base import Base
from core.db.mixins import GUID, UUIDPrimaryKeyMixin


class EventLogEntry(UUIDPrimaryKeyMixin, Base):
    """Append-only record of every published event. Used for audit/debugging
    ("why did Production start this work order?") and as the foundation for a
    future durable-broker upgrade requiring replay."""

    __tablename__ = "event_log"

    event_name: Mapped[str] = mapped_column(String, nullable=False, index=True)
    company_id: Mapped[str] = mapped_column(GUID(), ForeignKey("companies.id"), nullable=False, index=True)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    published_by_module: Mapped[str] = mapped_column(String, nullable=False)
    processed_by: Mapped[List[str]] = mapped_column(JSON, nullable=False, default=list)
    occurred_at: Mapped[object] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
