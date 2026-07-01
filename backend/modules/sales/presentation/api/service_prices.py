from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from core.db.session import get_db
from core.rbac.dependencies import CurrentUser, require_permission
from modules.sales.application.dtos import UpsertServicePriceInput
from modules.sales.application.use_cases import UpsertServicePriceUseCase
from modules.sales.infrastructure.repositories.service_price_repository import ServicePriceRepository
from modules.sales.presentation.schemas.service_price import (
    ServicePriceListOut,
    ServicePriceOut,
    ServicePriceUpsert,
)

router = APIRouter()


@router.get("/service-prices", response_model=ServicePriceListOut)
def list_service_prices(
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("sales:settings:read")),
) -> ServicePriceListOut:
    items = ServicePriceRepository(db).list_for_company(
        company_id=current_user.active_company_id
    )
    return ServicePriceListOut(items=[ServicePriceOut.model_validate(p) for p in items])


@router.put("/service-prices", response_model=ServicePriceOut)
def upsert_service_price(
    payload: ServicePriceUpsert,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("sales:settings:write")),
) -> ServicePriceOut:
    uc = UpsertServicePriceUseCase(db)
    price = uc.execute(
        UpsertServicePriceInput(
            company_id=current_user.active_company_id,
            actor_user_id=current_user.user_id,
            service_key=payload.service_key,
            sale_price=payload.sale_price,
            cost_price=payload.cost_price,
        )
    )
    db.commit()
    db.refresh(price)
    return ServicePriceOut.model_validate(price)
