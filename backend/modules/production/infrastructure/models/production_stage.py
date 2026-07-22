from sqlalchemy import Boolean, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from core.db.base import Base
from core.db.mixins import GUID, TimestampMixin, UUIDPrimaryKeyMixin


class ProductionStage(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A per-company, configurable step in the shop-floor pipeline (e.g.
    Measuring, CNC, Polishing). Seeded with 8 stone-fabrication defaults the
    first time a company's stage list is requested and none exist yet
    (`ProductionStageRepository.list_or_seed_defaults`); freely renamable,
    reorderable, and hideable afterward -- this is what makes the
    production stage pipeline "configurable" rather than a hardcoded enum."""

    __tablename__ = "production_stages"
    __table_args__ = (UniqueConstraint("company_id", "name", name="uq_production_stage_name_per_company"),)

    company_id: Mapped[str] = mapped_column(GUID(), ForeignKey("companies.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
