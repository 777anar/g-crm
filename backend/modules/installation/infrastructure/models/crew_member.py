from sqlalchemy import Boolean, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from core.db.base import Base
from core.db.mixins import GUID, TimestampMixin, UUIDPrimaryKeyMixin


class CrewMember(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "installation_crew_members"
    __table_args__ = (UniqueConstraint("crew_id", "user_id", name="uq_crew_member"),)

    company_id: Mapped[str] = mapped_column(GUID(), ForeignKey("companies.id"), nullable=False, index=True)
    crew_id: Mapped[str] = mapped_column(GUID(), ForeignKey("installation_crews.id"), nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(GUID(), ForeignKey("users.id"), nullable=False, index=True)
    is_lead: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
