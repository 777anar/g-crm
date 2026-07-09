from typing import Optional

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from core.db.base import Base
from core.db.mixins import GUID, TimestampMixin, UUIDPrimaryKeyMixin
from modules.sales.domain.value_objects import ROOM_TYPE_CUSTOM


class Room(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A physical space ("Məkan") within a Project -- Kitchen, Bathroom, ...
    Project Items belong to a Room. Independent of any Quote version's
    Sections, which are a pricing-document grouping, not a project-planning one."""

    __tablename__ = "sales_rooms"

    company_id: Mapped[str] = mapped_column(GUID(), ForeignKey("companies.id"), nullable=False, index=True)
    project_id: Mapped[str] = mapped_column(GUID(), ForeignKey("sales_projects.id"), nullable=False, index=True)

    room_type: Mapped[str] = mapped_column(String(50), nullable=False, default=ROOM_TYPE_CUSTOM)
    name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
