import csv
import io
import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session

from core.api.errors import ConflictError, NotFoundError
from core.api.pagination import decode_cursor, encode_cursor
from core.db.session import get_db
from core.rbac.dependencies import CurrentUser, require_permission
from modules.crm.application.dtos import ConvertLeadInput, CreateLeadInput
from modules.crm.application.use_cases import ConvertLeadUseCase, CreateLeadUseCase
from modules.crm.domain.exceptions import LeadAlreadyConvertedError
from modules.crm.infrastructure.repositories.lead_repository import LeadRepository
from modules.crm.presentation.schemas.lead import LeadConvertOut, LeadCreate, LeadListOut, LeadOut

router = APIRouter()


@router.get("/leads", response_model=LeadListOut)
def list_leads(
    status: Optional[str] = Query(default=None),
    source_channel: Optional[str] = Query(default=None),
    search: Optional[str] = Query(default=None, description="Matches full name, phone, email, or campaign"),
    sort: Optional[str] = Query(default=None, description="One of full_name, created_at, status; prefix with - for descending"),
    limit: int = Query(default=25, le=100),
    cursor: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("crm:leads:read")),
) -> LeadListOut:
    repo = LeadRepository(db)
    offset = decode_cursor(cursor)
    items = repo.list(
        company_id=current_user.active_company_id,
        status=status,
        source_channel=source_channel,
        search=search,
        sort=sort,
        limit=limit + 1,
        offset=offset,
    )
    has_more = len(items) > limit
    page = items[:limit]
    next_cursor = encode_cursor(offset=offset + limit) if has_more else None
    return LeadListOut(items=[LeadOut.model_validate(lead) for lead in page], next_cursor=next_cursor)


LEAD_EXPORT_LIMIT = 10_000

_LEAD_CSV_HEADER = [
    "id",
    "full_name",
    "source_channel",
    "status",
    "email",
    "phone",
    "campaign",
    "assigned_manager_id",
    "converted_customer_id",
    "created_at",
]


def _lead_csv_row(lead) -> list:
    return [
        str(lead.id),
        lead.full_name,
        lead.source_channel,
        lead.status,
        lead.email or "",
        lead.phone or "",
        lead.campaign or "",
        str(lead.assigned_manager_id) if lead.assigned_manager_id else "",
        str(lead.converted_customer_id) if lead.converted_customer_id else "",
        lead.created_at.isoformat() if lead.created_at else "",
    ]


@router.get("/leads/export")
def export_leads(
    status: Optional[str] = Query(default=None),
    source_channel: Optional[str] = Query(default=None),
    search: Optional[str] = Query(default=None),
    sort: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("crm:leads:read")),
) -> Response:
    repo = LeadRepository(db)
    items = repo.list(
        company_id=current_user.active_company_id,
        status=status,
        source_channel=source_channel,
        search=search,
        sort=sort,
        limit=LEAD_EXPORT_LIMIT,
        offset=0,
    )
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(_LEAD_CSV_HEADER)
    for lead in items:
        writer.writerow(_lead_csv_row(lead))
    content = ("﻿" + buffer.getvalue()).encode("utf-8")
    return Response(
        content=content,
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="leads.csv"'},
    )


@router.post("/leads", response_model=LeadOut)
def create_lead(
    payload: LeadCreate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("crm:leads:write")),
) -> LeadOut:
    use_case = CreateLeadUseCase(db)
    lead = use_case.execute(
        CreateLeadInput(
            company_id=current_user.active_company_id,
            actor_user_id=current_user.user_id,
            full_name=payload.full_name,
            source_channel=payload.source_channel,
            email=payload.email,
            phone=payload.phone,
            campaign=payload.campaign,
            campaign_id=payload.campaign_id,
            assigned_manager_id=payload.assigned_manager_id,
        )
    )
    db.commit()
    db.refresh(lead)
    return LeadOut.model_validate(lead)


@router.get("/leads/{lead_id}", response_model=LeadOut)
def get_lead(
    lead_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("crm:leads:read")),
) -> LeadOut:
    repo = LeadRepository(db)
    lead = repo.get(company_id=current_user.active_company_id, lead_id=lead_id)
    if lead is None:
        raise NotFoundError("Lead not found")
    return LeadOut.model_validate(lead)


@router.post("/leads/{lead_id}/convert", response_model=LeadConvertOut)
def convert_lead(
    lead_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("crm:leads:write")),
) -> LeadConvertOut:
    use_case = ConvertLeadUseCase(db)
    try:
        customer = use_case.execute(
            ConvertLeadInput(
                company_id=current_user.active_company_id,
                actor_user_id=current_user.user_id,
                lead_id=lead_id,
            )
        )
    except LeadAlreadyConvertedError as exc:
        raise ConflictError(str(exc)) from exc
    db.commit()
    return LeadConvertOut(customer_id=customer.id, contact_id=customer.primary_contact_id)
