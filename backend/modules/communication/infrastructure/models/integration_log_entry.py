from typing import Any, Optional

from sqlalchemy import Boolean, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from core.db.base import Base
from core.db.mixins import GUID, TimestampMixin, UUIDPrimaryKeyMixin


class IntegrationLogEntry(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """One provider interaction -- either something we did (`outbound`:
    send_message, test_connection, token_refresh, imap_sync) or something a
    provider sent us (`inbound`: a webhook delivery). One table,
    discriminated by `direction`/`action`, rather than a separate table per
    concern -- the same pattern AIRecommendation established for the AI
    module's 27 recommendation types. Backs three admin surfaces at once:
    Provider Diagnostics, Logs, and the Webhook Monitor (direction=inbound)."""

    __tablename__ = "communication_integration_logs"

    company_id: Mapped[Optional[str]] = mapped_column(GUID(), ForeignKey("companies.id"), nullable=True, index=True)
    channel_id: Mapped[Optional[str]] = mapped_column(
        GUID(), ForeignKey("communication_channels.id"), nullable=True, index=True
    )
    provider: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    direction: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(30), nullable=False, index=True)

    success: Mapped[bool] = mapped_column(Boolean, nullable=False)
    status_code: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    signature_valid: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    duration_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    payload: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
