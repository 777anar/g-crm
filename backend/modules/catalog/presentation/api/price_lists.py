import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from core.api.errors import NotFoundError
from core.db.session import get_db
from core.rbac.dependencies import CurrentUser, require_permission
from modules.catalog.application.dtos import CreatePriceListInput, UpsertPriceListEntryInput
from modules.catalog.application.use_cases import CreatePriceListUseCase, UpsertPriceListEntryUseCase
from modules.catalog.infrastructure.repositories.price_list_repository import (
    PriceListEntryRepository,
    PriceListRepository,
)
from modules.catalog.presentation.schemas.price_list import (
    PriceListCreate,
    PriceListEntryListOut,
    PriceListEntryOut,
    PriceListEntryUpsert,
    PriceListListOut,
    PriceListOut,
)

router = APIRouter()


@router.get("/price-lists", response_model=PriceListListOut)
def list_price_lists(
    include_hidden: bool = Query(default=False),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("catalog:price_lists:read")),
) -> PriceListListOut:
    repo = PriceListRepository(db)
    items = repo.list(company_id=current_user.active_company_id, include_hidden=include_hidden)
    return PriceListListOut(items=[PriceListOut.model_validate(p) for p in items])


@router.post("/price-lists", response_model=PriceListOut)
def create_price_list(
    payload: PriceListCreate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("catalog:price_lists:write")),
) -> PriceListOut:
    use_case = CreatePriceListUseCase(db)
    price_list = use_case.execute(
        CreatePriceListInput(
            company_id=current_user.active_company_id,
            actor_user_id=current_user.user_id,
            name=payload.name,
            currency=payload.currency,
            is_default=payload.is_default,
        )
    )
    db.commit()
    db.refresh(price_list)
    return PriceListOut.model_validate(price_list)


@router.get("/price-lists/{price_list_id}", response_model=PriceListOut)
def get_price_list(
    price_list_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("catalog:price_lists:read")),
) -> PriceListOut:
    repo = PriceListRepository(db)
    price_list = repo.get(company_id=current_user.active_company_id, price_list_id=price_list_id)
    if price_list is None:
        raise NotFoundError("Price list not found")
    return PriceListOut.model_validate(price_list)


@router.get("/price-lists/{price_list_id}/entries", response_model=PriceListEntryListOut)
def list_price_list_entries(
    price_list_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("catalog:price_lists:read")),
) -> PriceListEntryListOut:
    repo = PriceListEntryRepository(db)
    items = repo.list_for_price_list(company_id=current_user.active_company_id, price_list_id=price_list_id)
    return PriceListEntryListOut(items=[PriceListEntryOut.model_validate(e) for e in items])


@router.put("/price-lists/{price_list_id}/entries", response_model=PriceListEntryOut)
def upsert_price_list_entry(
    price_list_id: uuid.UUID,
    payload: PriceListEntryUpsert,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("catalog:price_lists:write")),
) -> PriceListEntryOut:
    use_case = UpsertPriceListEntryUseCase(db)
    entry = use_case.execute(
        UpsertPriceListEntryInput(
            company_id=current_user.active_company_id,
            actor_user_id=current_user.user_id,
            price_list_id=price_list_id,
            material_id=payload.material_id,
            cost_price=payload.cost_price,
            sale_price=payload.sale_price,
        )
    )
    db.commit()
    db.refresh(entry)
    return PriceListEntryOut.model_validate(entry)


@router.get("/materials/{material_id}/prices", response_model=PriceListEntryListOut)
def list_prices_for_material(
    material_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("catalog:price_lists:read")),
) -> PriceListEntryListOut:
    """Convenience endpoint for the Material detail screen: every price-list
    entry that prices this one material, across all of the company's price
    lists, in one call."""
    repo = PriceListEntryRepository(db)
    items = repo.list_for_material(company_id=current_user.active_company_id, material_id=material_id)
    return PriceListEntryListOut(items=[PriceListEntryOut.model_validate(e) for e in items])
