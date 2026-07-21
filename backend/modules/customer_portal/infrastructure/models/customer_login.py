from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from core.db.base import Base
from core.db.mixins import GUID, TimestampMixin, UUIDPrimaryKeyMixin


class CustomerLogin(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A customer's own portal login credential -- a separate identity from
    the staff `users` table (core/auth), one-to-one with a `crm_customers`
    row. A real FK to crm_customers.id is safe here (unlike crm_leads.campaign_id
    in the Marketing module): this table lives in customer_portal, which
    depends_on=["crm", ...], so the dependency direction stays module -> module
    it already declares, not core -> module or the reverse of an existing edge."""

    __tablename__ = "customer_portal_logins"

    company_id: Mapped[str] = mapped_column(GUID(), ForeignKey("companies.id"), nullable=False, index=True)
    customer_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("crm_customers.id"), nullable=False, unique=True, index=True
    )

    email: Mapped[str] = mapped_column(String, nullable=False, unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    last_login_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
