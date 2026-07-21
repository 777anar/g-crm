from typing import Optional

from sqlalchemy import ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from core.db.base import Base
from core.db.mixins import GUID, TimestampMixin, UUIDPrimaryKeyMixin
from modules.marketing.domain.value_objects import CAMPAIGN_STATUS_DRAFT, DEFAULT_CAMPAIGN_CURRENCY


class Campaign(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A marketing campaign. Leads captured while it's running are attributed
    to it via `crm_leads.campaign_id` -- an opaque, unconstrained reference
    (see that column's docstring), not a DB-level FK, so CRM never has to
    depend on this module even though attribution reads flow the other way."""

    __tablename__ = "campaigns"

    company_id: Mapped[str] = mapped_column(GUID(), ForeignKey("companies.id"), nullable=False, index=True)

    name: Mapped[str] = mapped_column(String, nullable=False)
    channel: Mapped[str] = mapped_column(String, nullable=False, index=True)
    status: Mapped[str] = mapped_column(String, nullable=False, default=CAMPAIGN_STATUS_DRAFT, index=True)

    start_date: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    end_date: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)

    budget: Mapped[Optional[str]] = mapped_column(Numeric(14, 2), nullable=True)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default=DEFAULT_CAMPAIGN_CURRENCY)

    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_by: Mapped[Optional[str]] = mapped_column(GUID(), ForeignKey("users.id"), nullable=True)
