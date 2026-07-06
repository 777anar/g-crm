from typing import List, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from core.db.base import Base
from core.db.mixins import GUID, TimestampMixin, UUIDPrimaryKeyMixin
from modules.crm.domain.value_objects import DEFAULT_TASK_PRIORITY, DEFAULT_TASK_STATUS


class Task(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A follow-up/reminder item, optionally assigned to a user and/or
    linked to another record (customer, lead, order, ...) via a polymorphic
    related_entity_type/related_entity_id pair -- the same pattern
    core.audit_log already uses, since a task needs to be able to point at
    literally any entity in the system without this module depending on
    every other module's domain."""

    __tablename__ = "crm_tasks"

    company_id: Mapped[str] = mapped_column(GUID(), ForeignKey("companies.id"), nullable=False, index=True)

    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default=DEFAULT_TASK_STATUS, index=True)
    priority: Mapped[str] = mapped_column(String(20), nullable=False, default=DEFAULT_TASK_PRIORITY, index=True)
    tags: Mapped[List[str]] = mapped_column(JSON, nullable=False, default=list)

    due_date: Mapped[Optional[str]] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    remind_at: Mapped[Optional[str]] = mapped_column(DateTime(timezone=True), nullable=True, index=True)

    assigned_to: Mapped[Optional[str]] = mapped_column(GUID(), ForeignKey("users.id"), nullable=True, index=True)

    related_entity_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)
    related_entity_id: Mapped[Optional[str]] = mapped_column(GUID(), nullable=True, index=True)

    # Recurrence: is_recurring/recurrence_rule/recurrence_interval describe
    # the template. series_id is null on the template task itself and set
    # to the template's id on every generated occurrence, so the whole
    # series can be listed without walking a linked list.
    is_recurring: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    recurrence_rule: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    recurrence_interval: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    recurrence_end_date: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    series_id: Mapped[Optional[str]] = mapped_column(GUID(), ForeignKey("crm_tasks.id"), nullable=True, index=True)

    completed_at: Mapped[Optional[str]] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_at: Mapped[Optional[str]] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Idempotency guards for GenerateDueTaskNotificationsUseCase -- each
    # reminder/overdue notification is created at most once per task.
    reminder_sent_at: Mapped[Optional[str]] = mapped_column(DateTime(timezone=True), nullable=True)
    overdue_notified_at: Mapped[Optional[str]] = mapped_column(DateTime(timezone=True), nullable=True)

    created_by: Mapped[Optional[str]] = mapped_column(GUID(), ForeignKey("users.id"), nullable=True)
