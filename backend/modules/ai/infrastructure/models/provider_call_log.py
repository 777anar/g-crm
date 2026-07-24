from typing import Optional

from sqlalchemy import Boolean, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from core.db.base import Base
from core.db.mixins import GUID, TimestampMixin, UUIDPrimaryKeyMixin


class AIProviderCallLog(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """One row per provider call -- mock or real -- so every AI-generated
    recommendation is traceable back to the exact prompt sent and the exact
    raw response received (Phase 21's "prompt/response audit logging"
    requirement), and so real spend is queryable for cost control
    (`RunProviderGuard.check_budget`, `modules/ai/application/use_cases/
    _shared.py`) instead of only estimable after the fact from
    `AIRecommendation.execution_time_ms`.

    Written for every call attempt, success or failure -- a rejected call
    (rate-limited, over budget, upstream error) is itself an operationally
    interesting row, not just a successful one."""

    __tablename__ = "ai_provider_call_logs"

    company_id: Mapped[str] = mapped_column(GUID(), ForeignKey("companies.id"), nullable=False, index=True)
    requested_by: Mapped[Optional[str]] = mapped_column(GUID(), ForeignKey("users.id"), nullable=True)

    analysis_kind: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    provider: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    model: Mapped[str] = mapped_column(String(100), nullable=False, default="")

    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    # Raw provider response text before JSON parsing -- null for the mock
    # provider, which never makes a real API call and has no raw text to
    # keep (see AIAnalysisResult's docstring).
    raw_response: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    input_tokens: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    output_tokens: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    cost_usd: Mapped[Optional[float]] = mapped_column(Numeric(10, 6), nullable=True)
    latency_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    success: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
