from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, func
from sqlalchemy.orm import Mapped, mapped_column

from core.db.base import Base
from core.db.mixins import GUID, TimestampMixin, UUIDPrimaryKeyMixin


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


class AuditRetentionPolicy(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """One row per company (Phase 18's compliance/audit-export admin surface).

    `retention_days=None` means "keep forever" (the default -- the append-only
    log's original guarantee is unaffected until an owner explicitly opts
    into a retention window). Purging is a manual, owner-triggered action
    (POST /api/v1/audit/retention-policy/purge), not an automatic background
    job: there is no job queue in this codebase yet (see
    MASTER_DEVELOPMENT_ROADMAP.md Phase 24), so promising silent automatic
    deletion here would be exactly the kind of unimplemented promise Phase 18
    exists to close, not add."""

    __tablename__ = "audit_retention_policies"

    company_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("companies.id"), nullable=False, unique=True, index=True
    )
    retention_days: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    updated_by: Mapped[str] = mapped_column(GUID(), ForeignKey("users.id"), nullable=False)
