import csv
import io
import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session

from core.api.errors import ConflictError
from core.api.pagination import decode_cursor, encode_cursor
from core.db.session import get_db
from core.rbac.dependencies import CurrentUser, require_permission
from modules.crm.application.dtos import (
    AddCustomerNoteInput,
    ArchiveCustomerInput,
    CreateCustomerInput,
    RestoreCustomerInput,
    UpdateCustomerInput,
)
from modules.crm.application.use_cases import (
    AddCustomerNoteUseCase,
    ArchiveCustomerUseCase,
    CreateCustomerUseCase,
    GetCustomerProfileUseCase,
    RestoreCustomerUseCase,
    UpdateCustomerUseCase,
)
from modules.crm.domain.exceptions import CustomerAlreadyArchivedError, CustomerNotArchivedError
from modules.crm.infrastructure.repositories.customer_repository import CustomerRepository
from modules.crm.presentation.schemas.customer import (
    ActivityOut,
    AddNoteRequest,
    AttachmentOut,
    ContactOut,
    CustomerCreate,
    CustomerListOut,
    CustomerOut,
    CustomerProfileOut,
    CustomerUpdate,
)

router = APIRouter()


@router.get("/customers", response_model=CustomerListOut)
def list_customers(
    include_archived: bool = Query(default=False),
    assigned_manager_id: Optional[uuid.UUID] = Query(default=None),
    status: Optional[str] = Query(default=None),
    lead_source: Optional[str] = Query(default=None),
    search: Optional[str] = Query(default=None, description="Matches name, phone, email, social handles, or company"),
    sort: Optional[str] = Query(default=None, description="One of name, created_at, updated_at, status; prefix with - for descending"),
    limit: int = Query(default=25, le=100),
    cursor: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("crm:customers:read")),
) -> CustomerListOut:
    repo = CustomerRepository(db)
    offset = decode_cursor(cursor)
    # Fetch one extra row past `limit` purely to detect whether a further
    # page exists -- never returned to the client.
    items = repo.list(
        company_id=current_user.active_company_id,
        include_archived=include_archived,
        assigned_manager_id=assigned_manager_id,
        status=status,
        lead_source=lead_source,
        search=search,
        sort=sort,
        limit=limit + 1,
        offset=offset,
    )
    has_more = len(items) > limit
    page = items[:limit]
    next_cursor = encode_cursor(offset=offset + limit) if has_more else None
    return CustomerListOut(items=[CustomerOut.model_validate(c) for c in page], next_cursor=next_cursor)


CUSTOMER_EXPORT_LIMIT = 10_000

_CUSTOMER_CSV_HEADER = [
    "id",
    "name",
    "type",
    "status",
    "assigned_manager_id",
    "lead_source",
    "advertising_campaign",
    "phone",
    "whatsapp",
    "instagram",
    "facebook",
    "email",
    "address",
    "company_name",
    "tags",
    "archived",
    "created_at",
    "updated_at",
]


def _customer_csv_row(customer) -> list:
    return [
        str(customer.id),
        customer.name,
        customer.type,
        customer.status,
        str(customer.assigned_manager_id) if customer.assigned_manager_id else "",
        customer.lead_source or "",
        customer.advertising_campaign or "",
        customer.phone or "",
        customer.whatsapp or "",
        customer.instagram or "",
        customer.facebook or "",
        customer.email or "",
        customer.address or "",
        customer.company_name or "",
        ";".join(customer.tags or []),
        "yes" if customer.deleted_at else "no",
        customer.created_at.isoformat() if customer.created_at else "",
        customer.updated_at.isoformat() if customer.updated_at else "",
    ]


@router.get("/customers/export")
def export_customers(
    include_archived: bool = Query(default=False),
    assigned_manager_id: Optional[uuid.UUID] = Query(default=None),
    status: Optional[str] = Query(default=None),
    lead_source: Optional[str] = Query(default=None),
    search: Optional[str] = Query(default=None),
    sort: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("crm:customers:read")),
) -> Response:
    repo = CustomerRepository(db)
    items = repo.list(
        company_id=current_user.active_company_id,
        include_archived=include_archived,
        assigned_manager_id=assigned_manager_id,
        status=status,
        lead_source=lead_source,
        search=search,
        sort=sort,
        limit=CUSTOMER_EXPORT_LIMIT,
        offset=0,
    )
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(_CUSTOMER_CSV_HEADER)
    for customer in items:
        writer.writerow(_customer_csv_row(customer))
    # Leading BOM so Excel (the realistic destination for this file)
    # detects UTF-8 instead of guessing a legacy codepage and mangling
    # Azerbaijani/Cyrillic characters.
    content = ("﻿" + buffer.getvalue()).encode("utf-8")
    return Response(
        content=content,
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="customers.csv"'},
    )


@router.post("/customers", response_model=CustomerOut)
def create_customer(
    payload: CustomerCreate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("crm:customers:write")),
) -> CustomerOut:
    use_case = CreateCustomerUseCase(db)
    customer = use_case.execute(
        CreateCustomerInput(
            company_id=current_user.active_company_id,
            actor_user_id=current_user.user_id,
            name=payload.name,
            type=payload.type,
            assigned_manager_id=payload.assigned_manager_id,
            lead_source=payload.lead_source,
            advertising_campaign=payload.advertising_campaign,
            phone=payload.phone,
            whatsapp=payload.whatsapp,
            instagram=payload.instagram,
            facebook=payload.facebook,
            email=payload.email,
            address=payload.address,
            company_name=payload.company_name,
            notes=payload.notes,
            status=payload.status,
            tags=payload.tags,
            contact_full_name=payload.contact.full_name if payload.contact else None,
            contact_email=payload.contact.email if payload.contact else None,
            contact_phone=payload.contact.phone if payload.contact else None,
        )
    )
    db.commit()
    db.refresh(customer)
    return CustomerOut.model_validate(customer)


@router.get("/customers/{customer_id}", response_model=CustomerOut)
def get_customer(
    customer_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("crm:customers:read")),
) -> CustomerOut:
    repo = CustomerRepository(db)
    customer = repo.get_model(company_id=current_user.active_company_id, customer_id=customer_id)
    if customer is None:
        from core.api.errors import NotFoundError

        raise NotFoundError("Customer not found")
    return CustomerOut.model_validate(customer)


@router.patch("/customers/{customer_id}", response_model=CustomerOut)
def update_customer(
    customer_id: uuid.UUID,
    payload: CustomerUpdate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("crm:customers:write")),
) -> CustomerOut:
    use_case = UpdateCustomerUseCase(db)
    customer = use_case.execute(
        UpdateCustomerInput(
            company_id=current_user.active_company_id,
            actor_user_id=current_user.user_id,
            customer_id=customer_id,
            name=payload.name,
            type=payload.type,
            assigned_manager_id=payload.assigned_manager_id,
            clear_assigned_manager="assigned_manager_id" in payload.model_fields_set
            and payload.assigned_manager_id is None,
            lead_source=payload.lead_source,
            advertising_campaign=payload.advertising_campaign,
            phone=payload.phone,
            whatsapp=payload.whatsapp,
            instagram=payload.instagram,
            facebook=payload.facebook,
            email=payload.email,
            address=payload.address,
            company_name=payload.company_name,
            notes=payload.notes,
            status=payload.status,
            tags=payload.tags,
        )
    )
    db.commit()
    db.refresh(customer)
    return CustomerOut.model_validate(customer)


@router.delete("/customers/{customer_id}", response_model=CustomerOut)
def archive_customer(
    customer_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("crm:customers:write")),
) -> CustomerOut:
    use_case = ArchiveCustomerUseCase(db)
    try:
        customer = use_case.execute(
            ArchiveCustomerInput(
                company_id=current_user.active_company_id,
                actor_user_id=current_user.user_id,
                customer_id=customer_id,
            )
        )
    except CustomerAlreadyArchivedError as exc:
        raise ConflictError(str(exc)) from exc
    db.commit()
    db.refresh(customer)
    return CustomerOut.model_validate(customer)


@router.post("/customers/{customer_id}/restore", response_model=CustomerOut)
def restore_customer(
    customer_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("crm:customers:write")),
) -> CustomerOut:
    use_case = RestoreCustomerUseCase(db)
    try:
        customer = use_case.execute(
            RestoreCustomerInput(
                company_id=current_user.active_company_id,
                actor_user_id=current_user.user_id,
                customer_id=customer_id,
            )
        )
    except CustomerNotArchivedError as exc:
        raise ConflictError(str(exc)) from exc
    db.commit()
    db.refresh(customer)
    return CustomerOut.model_validate(customer)


@router.get("/customers/{customer_id}/profile", response_model=CustomerProfileOut)
def get_customer_profile(
    customer_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("crm:customers:read")),
) -> CustomerProfileOut:
    use_case = GetCustomerProfileUseCase(db)
    profile = use_case.execute(company_id=current_user.active_company_id, customer_id=customer_id)
    return CustomerProfileOut(
        customer=CustomerOut.model_validate(profile.customer),
        contacts=[ContactOut.model_validate(c) for c in profile.contacts],
        attachments=[AttachmentOut.model_validate(a) for a in profile.attachments],
        timeline=[ActivityOut.model_validate(a) for a in profile.timeline],
        projects=profile.projects,
        quotes=profile.quotes,
        orders=profile.orders,
        payments=profile.payments,
    )


@router.get("/customers/{customer_id}/notes", response_model=List[ActivityOut])
def list_customer_notes(
    customer_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("crm:notes:read")),
) -> List[ActivityOut]:
    from modules.crm.domain.value_objects import ACTIVITY_TYPE_NOTE
    from modules.crm.infrastructure.repositories.activity_repository import ActivityRepository

    repo = ActivityRepository(db)
    notes = repo.list_for_entity(
        company_id=current_user.active_company_id,
        related_entity_type="customer",
        related_entity_id=customer_id,
        type_filter=ACTIVITY_TYPE_NOTE,
    )
    return [ActivityOut.model_validate(n) for n in notes]


@router.get("/customers/{customer_id}/attachments", response_model=List[AttachmentOut])
def list_customer_attachments(
    customer_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("crm:attachments:read")),
) -> List[AttachmentOut]:
    """Attachments are uploaded via the shared core endpoint
    (POST /api/v1/core/documents with module=crm, related_entity_type=customer)
    so file storage logic lives in exactly one place. This endpoint lists
    them scoped to a customer for the profile screen."""
    from core.storage.models import Document

    rows = (
        db.query(Document)
        .filter(
            Document.company_id == current_user.active_company_id,
            Document.related_entity_type == "customer",
            Document.related_entity_id == customer_id,
        )
        .order_by(Document.created_at.desc())
        .all()
    )
    return [AttachmentOut.model_validate(r) for r in rows]


@router.post("/customers/{customer_id}/notes", response_model=ActivityOut)
def add_customer_note(
    customer_id: uuid.UUID,
    payload: AddNoteRequest,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("crm:notes:write")),
) -> ActivityOut:
    use_case = AddCustomerNoteUseCase(db)
    note = use_case.execute(
        AddCustomerNoteInput(
            company_id=current_user.active_company_id,
            actor_user_id=current_user.user_id,
            customer_id=customer_id,
            body=payload.body,
        )
    )
    db.commit()
    db.refresh(note)
    return ActivityOut.model_validate(note)
