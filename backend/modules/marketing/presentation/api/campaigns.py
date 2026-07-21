import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from core.api.errors import BusinessRuleViolationError, NotFoundError
from core.api.pagination import decode_cursor, encode_cursor
from core.db.session import get_db
from core.rbac.dependencies import CurrentUser, require_permission
from modules.marketing.application.dtos import (
    CreateCampaignInput,
    GetCampaignPerformanceInput,
    UpdateCampaignInput,
    UpdateCampaignStatusInput,
)
from modules.marketing.application.use_cases import (
    CreateCampaignUseCase,
    GetCampaignPerformanceUseCase,
    UpdateCampaignStatusUseCase,
    UpdateCampaignUseCase,
)
from modules.marketing.domain.exceptions import CampaignImmutableError, InvalidCampaignTransitionError
from modules.marketing.infrastructure.repositories.campaign_repository import CampaignRepository
from modules.marketing.presentation.schemas.campaign import (
    CampaignCreate,
    CampaignListOut,
    CampaignOut,
    CampaignPerformanceOut,
    CampaignStatusUpdate,
    CampaignUpdate,
)

router = APIRouter()

_BUSINESS_RULE_ERRORS = (CampaignImmutableError, InvalidCampaignTransitionError, ValueError)


@router.get("/campaigns", response_model=CampaignListOut)
def list_campaigns(
    status: Optional[str] = Query(default=None),
    channel: Optional[str] = Query(default=None),
    search: Optional[str] = Query(default=None),
    sort: Optional[str] = Query(default=None),
    limit: int = Query(default=25, le=100),
    cursor: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("marketing:campaigns:read")),
) -> CampaignListOut:
    repo = CampaignRepository(db)
    offset = decode_cursor(cursor)
    items = repo.list(
        company_id=current_user.active_company_id,
        status=status,
        channel=channel,
        search=search,
        sort=sort,
        limit=limit + 1,
        offset=offset,
    )
    has_more = len(items) > limit
    page = items[:limit]
    next_cursor = encode_cursor(offset=offset + limit) if has_more else None
    return CampaignListOut(items=[CampaignOut.model_validate(c) for c in page], next_cursor=next_cursor)


@router.post("/campaigns", response_model=CampaignOut)
def create_campaign(
    payload: CampaignCreate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("marketing:campaigns:write")),
) -> CampaignOut:
    campaign = CreateCampaignUseCase(db).execute(
        CreateCampaignInput(
            company_id=current_user.active_company_id,
            actor_user_id=current_user.user_id,
            name=payload.name,
            channel=payload.channel,
            start_date=payload.start_date,
            end_date=payload.end_date,
            budget=payload.budget,
            currency=payload.currency,
            notes=payload.notes,
        )
    )
    db.commit()
    db.refresh(campaign)
    return CampaignOut.model_validate(campaign)


@router.get("/campaigns/{campaign_id}", response_model=CampaignOut)
def get_campaign(
    campaign_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("marketing:campaigns:read")),
) -> CampaignOut:
    campaign = CampaignRepository(db).get(company_id=current_user.active_company_id, campaign_id=campaign_id)
    if campaign is None:
        raise NotFoundError("Campaign not found")
    return CampaignOut.model_validate(campaign)


@router.patch("/campaigns/{campaign_id}", response_model=CampaignOut)
def update_campaign(
    campaign_id: uuid.UUID,
    payload: CampaignUpdate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("marketing:campaigns:write")),
) -> CampaignOut:
    uc = UpdateCampaignUseCase(db)
    try:
        campaign = uc.execute(
            UpdateCampaignInput(
                company_id=current_user.active_company_id,
                actor_user_id=current_user.user_id,
                campaign_id=campaign_id,
                name=payload.name,
                channel=payload.channel,
                start_date=payload.start_date,
                end_date=payload.end_date,
                budget=payload.budget,
                notes=payload.notes,
            )
        )
    except _BUSINESS_RULE_ERRORS as exc:
        raise BusinessRuleViolationError(str(exc)) from exc
    db.commit()
    db.refresh(campaign)
    return CampaignOut.model_validate(campaign)


@router.post("/campaigns/{campaign_id}/status", response_model=CampaignOut)
def update_campaign_status(
    campaign_id: uuid.UUID,
    payload: CampaignStatusUpdate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("marketing:campaigns:write")),
) -> CampaignOut:
    uc = UpdateCampaignStatusUseCase(db)
    try:
        campaign = uc.execute(
            UpdateCampaignStatusInput(
                company_id=current_user.active_company_id,
                actor_user_id=current_user.user_id,
                campaign_id=campaign_id,
                status=payload.status,
            )
        )
    except _BUSINESS_RULE_ERRORS as exc:
        raise BusinessRuleViolationError(str(exc)) from exc
    db.commit()
    db.refresh(campaign)
    return CampaignOut.model_validate(campaign)


@router.get("/campaigns/{campaign_id}/performance", response_model=CampaignPerformanceOut)
def get_campaign_performance(
    campaign_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("marketing:campaigns:read")),
) -> CampaignPerformanceOut:
    performance = GetCampaignPerformanceUseCase(db).execute(
        GetCampaignPerformanceInput(
            company_id=current_user.active_company_id,
            actor_user_id=current_user.user_id,
            campaign_id=campaign_id,
        )
    )
    return CampaignPerformanceOut(
        leads_count=performance.leads_count,
        converted_count=performance.converted_count,
        conversion_rate=performance.conversion_rate,
        attributed_revenue=performance.attributed_revenue,
    )
