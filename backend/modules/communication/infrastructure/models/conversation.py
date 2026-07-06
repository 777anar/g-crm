from typing import List, Optional

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from core.db.base import Base
from core.db.mixins import GUID, TimestampMixin, UUIDPrimaryKeyMixin
from modules.communication.domain.value_objects import DEFAULT_CONVERSATION_STATUS


class Conversation(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """One message thread with one external contact on one Channel.
    customer_id/lead_id identify who the counterpart is in CRM (see
    GetOrCreateConversationUseCase); project_id/quote_id/order_id are
    optional links an agent can attach once the conversation is about a
    specific deal in progress."""

    __tablename__ = "communication_conversations"

    company_id: Mapped[str] = mapped_column(GUID(), ForeignKey("companies.id"), nullable=False, index=True)
    channel_id: Mapped[str] = mapped_column(GUID(), ForeignKey("communication_channels.id"), nullable=False, index=True)

    customer_id: Mapped[Optional[str]] = mapped_column(GUID(), ForeignKey("crm_customers.id"), nullable=True, index=True)
    lead_id: Mapped[Optional[str]] = mapped_column(GUID(), ForeignKey("crm_leads.id"), nullable=True, index=True)
    project_id: Mapped[Optional[str]] = mapped_column(GUID(), ForeignKey("sales_projects.id"), nullable=True, index=True)
    quote_id: Mapped[Optional[str]] = mapped_column(GUID(), ForeignKey("sales_quotes.id"), nullable=True, index=True)
    order_id: Mapped[Optional[str]] = mapped_column(GUID(), ForeignKey("orders.id"), nullable=True, index=True)

    external_contact_id: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    external_contact_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)

    status: Mapped[str] = mapped_column(String(20), nullable=False, default=DEFAULT_CONVERSATION_STATUS, index=True)
    assigned_to: Mapped[Optional[str]] = mapped_column(GUID(), ForeignKey("users.id"), nullable=True, index=True)
    tags: Mapped[List[str]] = mapped_column(JSON, nullable=False, default=list)

    unread_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_message_at: Mapped[Optional[str]] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    last_message_preview: Mapped[Optional[str]] = mapped_column(String(300), nullable=True)

    created_by: Mapped[Optional[str]] = mapped_column(GUID(), ForeignKey("users.id"), nullable=True)
