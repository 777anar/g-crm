from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from core.db.base import Base
from core.db.mixins import GUID, TimestampMixin, UUIDPrimaryKeyMixin
from modules.communication.domain.value_objects import HEALTH_STATUS_UNKNOWN


class ChannelCredential(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """The real-provider configuration for one Channel -- at most one row per
    channel. `encrypted_config` is a Fernet-encrypted JSON blob (see
    infrastructure/security/encryption.py) holding every field the chosen
    provider needs (tokens, host/port, account SIDs, ...); the raw value
    never appears in an API response, only masked
    (presentation/schemas/channel_credential.py).

    A Channel with no ChannelCredential row -- the default for every
    existing and newly-created channel -- keeps using NullChannelProvider
    exactly as before Version 2.9; configuring a credential is what
    "upgrades" a channel to a real integration."""

    __tablename__ = "communication_channel_credentials"

    company_id: Mapped[str] = mapped_column(GUID(), ForeignKey("companies.id"), nullable=False, index=True)
    channel_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("communication_channels.id"), nullable=False, unique=True, index=True
    )
    provider: Mapped[str] = mapped_column(String(30), nullable=False)

    encrypted_config: Mapped[str] = mapped_column(Text, nullable=False)
    webhook_secret_encrypted: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # IMAP sync cursor -- the highest UID already pulled into a Message row,
    # so SyncImapMailboxUseCase only ever fetches what's new.
    imap_last_synced_uid: Mapped[Optional[int]] = mapped_column(nullable=True)

    health_status: Mapped[str] = mapped_column(String(20), nullable=False, default=HEALTH_STATUS_UNKNOWN)
    last_checked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_by: Mapped[Optional[str]] = mapped_column(GUID(), ForeignKey("users.id"), nullable=True)
