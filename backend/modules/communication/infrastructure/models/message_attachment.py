from typing import Optional

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from core.db.base import Base
from core.db.mixins import GUID, TimestampMixin, UUIDPrimaryKeyMixin


class MessageAttachment(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A thin link from a Message to an already-uploaded core Document --
    reuses the shared storage pipeline (POST /api/v1/core/documents)
    exactly as Installation's photos and Catalog's material images do,
    rather than reimplementing file handling."""

    __tablename__ = "communication_message_attachments"

    company_id: Mapped[str] = mapped_column(GUID(), ForeignKey("companies.id"), nullable=False, index=True)
    message_id: Mapped[str] = mapped_column(GUID(), ForeignKey("communication_messages.id"), nullable=False, index=True)
    document_id: Mapped[str] = mapped_column(GUID(), ForeignKey("documents.id"), nullable=False, index=True)
    file_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
