from typing import Any, Optional

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from core.db.base import Base
from core.db.mixins import GUID, TimestampMixin, UUIDPrimaryKeyMixin
from modules.ai.domain.value_objects import DEFAULT_AI_PROVIDER, RECOMMENDATION_STATUS_PENDING


class AIRecommendation(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """One reviewable AI suggestion. Every kind of recommendation this
    module produces (lead score, conversation sentiment, quote upsell,
    task suggestion, ...) is a row in this one table, discriminated by
    `recommendation_type` -- not a separate table per type, since they all
    share the exact same reviewable-suggestion shape (a provider's
    structured output, pending a human accept/reject/edit decision) and
    splitting them would only duplicate that shape ~25 times.

    Nothing in this module ever writes to another module's tables as a
    side effect of analysis or of a review decision -- accepting a
    recommendation only changes `status` (and `edited_response`, if
    edited) on this row. See ReviewRecommendationUseCase's docstring for
    why: "AI never performs business actions automatically" is enforced
    structurally, not just by convention.
    """

    __tablename__ = "ai_recommendations"

    company_id: Mapped[str] = mapped_column(GUID(), ForeignKey("companies.id"), nullable=False, index=True)

    analysis_kind: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    recommendation_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    related_entity_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)
    related_entity_id: Mapped[Optional[str]] = mapped_column(GUID(), nullable=True, index=True)

    provider: Mapped[str] = mapped_column(String(50), nullable=False, default=DEFAULT_AI_PROVIDER, index=True)
    model: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    response: Mapped[Any] = mapped_column(JSON, nullable=False)
    # Phase 21: traces this recommendation back to the exact provider call
    # (prompt actually sent, raw response, token/cost figures) that produced
    # it -- nullable since recommendations created before this column existed
    # (and any future direct-insert path) have no call log to point to.
    provider_call_id: Mapped[Optional[str]] = mapped_column(
        GUID(), ForeignKey("ai_provider_call_logs.id"), nullable=True
    )
    confidence_score: Mapped[Optional[float]] = mapped_column(Numeric(4, 3), nullable=True)
    execution_time_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    summary: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default=RECOMMENDATION_STATUS_PENDING, index=True)
    edited_response: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)

    requested_by: Mapped[Optional[str]] = mapped_column(GUID(), ForeignKey("users.id"), nullable=True)
    reviewed_by: Mapped[Optional[str]] = mapped_column(GUID(), ForeignKey("users.id"), nullable=True)
    reviewed_at: Mapped[Optional[str]] = mapped_column(DateTime(timezone=True), nullable=True)
