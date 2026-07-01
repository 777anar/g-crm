from typing import Optional

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from core.db.base import Base
from core.db.mixins import GUID, TimestampMixin, UUIDPrimaryKeyMixin
from modules.sales.domain.value_objects import PROJECT_STATUS_ACTIVE, PROJECT_TYPE_OTHER


class Project(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "sales_projects"

    company_id: Mapped[str] = mapped_column(GUID(), ForeignKey("companies.id"), nullable=False, index=True)
    customer_id: Mapped[str] = mapped_column(GUID(), ForeignKey("crm_customers.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    project_type: Mapped[str] = mapped_column(String(50), nullable=False, default=PROJECT_TYPE_OTHER)
    address: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    assigned_to: Mapped[Optional[str]] = mapped_column(GUID(), ForeignKey("users.id"), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default=PROJECT_STATUS_ACTIVE, index=True)
