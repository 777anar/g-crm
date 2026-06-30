from typing import Optional

from sqlalchemy import DateTime, ForeignKey, JSON, String, func
from sqlalchemy.orm import Mapped, mapped_column

from core.db.base import Base
from core.db.mixins import GUID, UUIDPrimaryKeyMixin


class Document(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "documents"

    company_id: Mapped[str] = mapped_column(GUID(), ForeignKey("companies.id"), nullable=False, index=True)
    module: Mapped[str] = mapped_column(String, nullable=False)
    related_entity_type: Mapped[str] = mapped_column(String, nullable=False, index=True)
    related_entity_id: Mapped[str] = mapped_column(GUID(), nullable=False, index=True)
    storage_path: Mapped[str] = mapped_column(String, nullable=False)
    mime_type: Mapped[str] = mapped_column(String, nullable=False)
    uploaded_by: Mapped[str] = mapped_column(GUID(), ForeignKey("users.id"), nullable=False)
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class AIJob(UUIDPrimaryKeyMixin, Base):
    """Reserved now; populated starting in the AI module's phase. Lives in core
    because every module that triggers AI work shares this one job-tracking table."""

    __tablename__ = "ai_jobs"

    company_id: Mapped[str] = mapped_column(GUID(), ForeignKey("companies.id"), nullable=False, index=True)
    module: Mapped[str] = mapped_column(String, nullable=False)
    job_type: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False, default="queued")
    input_ref: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    result_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    celery_task_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    completed_at: Mapped[Optional[object]] = mapped_column(DateTime(timezone=True), nullable=True)
