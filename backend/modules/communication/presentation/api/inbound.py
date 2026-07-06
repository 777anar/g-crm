from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from core.db.session import get_db
from core.rbac.dependencies import CurrentUser, require_permission
from modules.communication.application.dtos import ReceiveInboundMessageInput
from modules.communication.application.use_cases import ReceiveInboundMessageUseCase
from modules.communication.presentation.schemas.message import InboundMessageCreate, MessageOut

router = APIRouter()


@router.post("/inbound", response_model=MessageOut)
def receive_inbound_message(
    payload: InboundMessageCreate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("communication:conversations:write")),
) -> MessageOut:
    """Stands in for a future real channel webhook (WhatsApp/Instagram/
    Messenger/email/SMS) -- see infrastructure/providers/base.py. Today this
    is an authenticated endpoint an agent (or a test harness) calls with the
    inbound payload; once a real provider exists, its webhook handler would
    call ReceiveInboundMessageUseCase directly instead, under its own
    signature-verification, not this route."""
    message = ReceiveInboundMessageUseCase(db).execute(
        ReceiveInboundMessageInput(
            company_id=current_user.active_company_id,
            actor_user_id=current_user.user_id,
            channel_id=payload.channel_id,
            external_contact_id=payload.external_contact_id,
            external_contact_name=payload.external_contact_name,
            body=payload.body,
            message_type=payload.message_type,
        )
    )
    db.commit()
    db.refresh(message)
    return MessageOut.model_validate(message)
