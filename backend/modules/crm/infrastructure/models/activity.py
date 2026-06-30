from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from core.db.base import Base
from core.db.mixins import GUID, UUIDPrimaryKeyMixin
from sqlalchemy import DateTime, func


class Activity(UUIDPrimaryKeyMixin, Base):
    """Notes, calls, emails, meetings, and system-generated entries
    (e.g., 'Lead converted to customer'). Powers both the dedicated Notes
    view and the aggregated Activity Timeline on a customer's profile."""

    __tablename__ = "crm_activities"

    company_id: Mapped[str] = mapped_column(GUID(), ForeignKey("companies.id"), nullable=False, index=True)
    type: Mapped[str] = mapped_column(String, nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    related_entity_type: Mapped[str] = mapped_column(String, nullable=False, index=True)
    related_entity_id: Mapped[str] = mapped_column(GUID(), nullable=False, index=True)
    created_by: Mapped[str] = mapped_column(GUID(), ForeignKey("users.id"), nullable=False)
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
