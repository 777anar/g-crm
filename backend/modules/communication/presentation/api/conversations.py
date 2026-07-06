import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from core.api.errors import BusinessRuleViolationError, NotFoundError
from core.api.pagination import decode_cursor, encode_cursor
from core.db.session import get_db
from core.rbac.dependencies import CurrentUser, require_permission
from modules.communication.application.dtos import (
    AddConversationNoteInput,
    AddMessageAttachmentInput,
    GetOrCreateConversationInput,
    MarkConversationReadInput,
    SendMessageInput,
    UpdateConversationInput,
)
from modules.communication.application.use_cases import (
    AddConversationNoteUseCase,
    AddMessageAttachmentUseCase,
    GetOrCreateConversationUseCase,
    MarkConversationReadUseCase,
    SendMessageUseCase,
    UpdateConversationUseCase,
)
from modules.communication.domain.exceptions import ChannelInactiveError
from modules.communication.infrastructure.repositories.conversation_note_repository import (
    ConversationNoteRepository,
)
from modules.communication.infrastructure.repositories.conversation_repository import ConversationRepository
from modules.communication.infrastructure.repositories.message_attachment_repository import (
    MessageAttachmentRepository,
)
from modules.communication.infrastructure.repositories.message_repository import MessageRepository
from modules.communication.presentation.schemas.conversation import (
    ConversationCreate,
    ConversationListOut,
    ConversationOut,
    ConversationUpdate,
)
from modules.communication.presentation.schemas.conversation_note import (
    ConversationNoteCreate,
    ConversationNoteListOut,
    ConversationNoteOut,
)
from modules.communication.presentation.schemas.message import (
    MessageAttachmentCreate,
    MessageAttachmentListOut,
    MessageAttachmentOut,
    MessageCreate,
    MessageListOut,
    MessageOut,
)

router = APIRouter()


@router.get("/conversations", response_model=ConversationListOut)
def list_conversations(
    channel_id: Optional[uuid.UUID] = Query(default=None),
    status: Optional[str] = Query(default=None),
    assigned_to: Optional[uuid.UUID] = Query(default=None),
    customer_id: Optional[uuid.UUID] = Query(default=None),
    lead_id: Optional[uuid.UUID] = Query(default=None),
    search: Optional[str] = Query(default=None, description="Matches contact name/id or last message preview"),
    sort: Optional[str] = Query(default=None, description="One of last_message_at, created_at, updated_at, status; prefix with - for descending"),
    limit: int = Query(default=25, le=100),
    cursor: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("communication:conversations:read")),
) -> ConversationListOut:
    repo = ConversationRepository(db)
    offset = decode_cursor(cursor)
    items = repo.list(
        company_id=current_user.active_company_id,
        channel_id=channel_id,
        status=status,
        assigned_to=assigned_to,
        customer_id=customer_id,
        lead_id=lead_id,
        search=search,
        sort=sort,
        limit=limit + 1,
        offset=offset,
    )
    has_more = len(items) > limit
    page = items[:limit]
    next_cursor = encode_cursor(offset=offset + limit) if has_more else None
    return ConversationListOut(items=[ConversationOut.model_validate(c) for c in page], next_cursor=next_cursor)


@router.post("/conversations", response_model=ConversationOut)
def start_conversation(
    payload: ConversationCreate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("communication:conversations:write")),
) -> ConversationOut:
    conversation = GetOrCreateConversationUseCase(db).execute(
        GetOrCreateConversationInput(
            company_id=current_user.active_company_id,
            actor_user_id=current_user.user_id,
            channel_id=payload.channel_id,
            external_contact_id=payload.external_contact_id,
            external_contact_name=payload.external_contact_name,
        )
    )
    db.commit()
    db.refresh(conversation)
    return ConversationOut.model_validate(conversation)


@router.get("/conversations/{conversation_id}", response_model=ConversationOut)
def get_conversation(
    conversation_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("communication:conversations:read")),
) -> ConversationOut:
    conversation = ConversationRepository(db).get(
        company_id=current_user.active_company_id, conversation_id=conversation_id
    )
    if conversation is None:
        raise NotFoundError("Conversation not found")
    return ConversationOut.model_validate(conversation)


@router.patch("/conversations/{conversation_id}", response_model=ConversationOut)
def update_conversation(
    conversation_id: uuid.UUID,
    payload: ConversationUpdate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("communication:conversations:write")),
) -> ConversationOut:
    conversation = UpdateConversationUseCase(db).execute(
        UpdateConversationInput(
            company_id=current_user.active_company_id,
            actor_user_id=current_user.user_id,
            conversation_id=conversation_id,
            status=payload.status,
            assigned_to=payload.assigned_to,
            tags=payload.tags,
            customer_id=payload.customer_id,
            lead_id=payload.lead_id,
            project_id=payload.project_id,
            quote_id=payload.quote_id,
            order_id=payload.order_id,
        )
    )
    db.commit()
    db.refresh(conversation)
    return ConversationOut.model_validate(conversation)


@router.post("/conversations/{conversation_id}/read", response_model=ConversationOut)
def mark_conversation_read(
    conversation_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("communication:conversations:write")),
) -> ConversationOut:
    conversation = MarkConversationReadUseCase(db).execute(
        MarkConversationReadInput(
            company_id=current_user.active_company_id,
            actor_user_id=current_user.user_id,
            conversation_id=conversation_id,
        )
    )
    db.commit()
    db.refresh(conversation)
    return ConversationOut.model_validate(conversation)


@router.get("/conversations/{conversation_id}/messages", response_model=MessageListOut)
def list_messages(
    conversation_id: uuid.UUID,
    limit: int = Query(default=100, le=200),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("communication:conversations:read")),
) -> MessageListOut:
    messages = MessageRepository(db).list_for_conversation(
        company_id=current_user.active_company_id, conversation_id=conversation_id, limit=limit
    )
    return MessageListOut(items=[MessageOut.model_validate(m) for m in messages])


@router.post("/conversations/{conversation_id}/messages", response_model=MessageOut)
def send_message(
    conversation_id: uuid.UUID,
    payload: MessageCreate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("communication:conversations:write")),
) -> MessageOut:
    try:
        message = SendMessageUseCase(db).execute(
            SendMessageInput(
                company_id=current_user.active_company_id,
                actor_user_id=current_user.user_id,
                conversation_id=conversation_id,
                body=payload.body,
                message_type=payload.message_type,
                template_id=payload.template_id,
            )
        )
    except ChannelInactiveError as exc:
        raise BusinessRuleViolationError(str(exc)) from exc
    db.commit()
    db.refresh(message)
    return MessageOut.model_validate(message)


@router.get("/conversations/{conversation_id}/notes", response_model=ConversationNoteListOut)
def list_conversation_notes(
    conversation_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("communication:notes:read")),
) -> ConversationNoteListOut:
    notes = ConversationNoteRepository(db).list_for_conversation(
        company_id=current_user.active_company_id, conversation_id=conversation_id
    )
    return ConversationNoteListOut(items=[ConversationNoteOut.model_validate(n) for n in notes])


@router.post("/conversations/{conversation_id}/notes", response_model=ConversationNoteOut)
def add_conversation_note(
    conversation_id: uuid.UUID,
    payload: ConversationNoteCreate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("communication:notes:write")),
) -> ConversationNoteOut:
    note = AddConversationNoteUseCase(db).execute(
        AddConversationNoteInput(
            company_id=current_user.active_company_id,
            actor_user_id=current_user.user_id,
            conversation_id=conversation_id,
            body=payload.body,
        )
    )
    db.commit()
    db.refresh(note)
    return ConversationNoteOut.model_validate(note)


@router.get(
    "/conversations/{conversation_id}/messages/{message_id}/attachments",
    response_model=MessageAttachmentListOut,
)
def list_message_attachments(
    conversation_id: uuid.UUID,
    message_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("communication:conversations:read")),
) -> MessageAttachmentListOut:
    attachments = MessageAttachmentRepository(db).list_for_message(
        company_id=current_user.active_company_id, message_id=message_id
    )
    return MessageAttachmentListOut(items=[MessageAttachmentOut.model_validate(a) for a in attachments])


@router.post(
    "/conversations/{conversation_id}/messages/{message_id}/attachments",
    response_model=MessageAttachmentOut,
)
def add_message_attachment(
    conversation_id: uuid.UUID,
    message_id: uuid.UUID,
    payload: MessageAttachmentCreate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("communication:conversations:write")),
) -> MessageAttachmentOut:
    attachment = AddMessageAttachmentUseCase(db).execute(
        AddMessageAttachmentInput(
            company_id=current_user.active_company_id,
            actor_user_id=current_user.user_id,
            message_id=message_id,
            document_id=payload.document_id,
            file_name=payload.file_name,
        )
    )
    db.commit()
    db.refresh(attachment)
    return MessageAttachmentOut.model_validate(attachment)
