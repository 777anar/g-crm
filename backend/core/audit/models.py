from typing import Optional

from sqlalchemy import DateTime, ForeignKey, JSON, String, func
from sqlalchemy.orm import Mapped, mapped_column

from core.db.base import Base
from core.db.mixins import GUID, UUIDPrimaryKeyMixin


class AuditLog(UUIDPrimaryKeyMixin, Base):
    """Append-only. No application code should ever UPDATE or DELETE a row here."""

    __tablename__ = "audit_log"

    company_id: Mapped[str] = mapped_column(GUID(), ForeignKey("companies.id"), nullable=False, index=True)
    module: Mapped[str] = mapped_column(String, nullable=False)
    actor_user_id: Mapped[str] = mapped_column(GUID(), ForeignKey("users.id"), nullable=False)
    action: Mapped[str] = mapped_column(String, nullable=False)
    entity_type: Mapped[str] = mapped_column(String, nullable=False, index=True)
    entity_id: Mapped[str] = mapped_column(GUID(), nullable=False, index=True)
    diff_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
