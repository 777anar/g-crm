import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from core.api.errors import NotFoundError
from core.api.pagination import decode_cursor, encode_cursor
from core.db.session import get_db
from core.rbac.dependencies import CurrentUser, require_permission
from modules.catalog.application.dtos import CreateBrandInput, UpdateBrandInput
from modules.catalog.application.use_cases import CreateBrandUseCase, UpdateBrandUseCase
from modules.catalog.infrastructure.repositories.brand_repository import BrandRepository
from modules.catalog.presentation.schemas.brand import BrandCreate, BrandListOut, BrandOut, BrandUpdate

router = APIRouter()


@router.get("/brands", response_model=BrandListOut)
def list_brands(
    include_hidden: bool = Query(default=False),
    search: Optional[str] = Query(default=None),
    limit: int = Query(default=25, le=100),
    cursor: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("catalog:brands:read")),
) -> BrandListOut:
    repo = BrandRepository(db)
    offset = decode_cursor(cursor)
    items = repo.list(
        company_id=current_user.active_company_id,
        include_hidden=include_hidden,
        search=search,
        limit=limit + 1,
        offset=offset,
    )
    has_more = len(items) > limit
    page = items[:limit]
    next_cursor = encode_cursor(offset=offset + limit) if has_more else None
    return BrandListOut(items=[BrandOut.model_validate(b) for b in page], next_cursor=next_cursor)


@router.post("/brands", response_model=BrandOut)
def create_brand(
    payload: BrandCreate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("catalog:brands:write")),
) -> BrandOut:
    use_case = CreateBrandUseCase(db)
    brand = use_case.execute(
        CreateBrandInput(
            company_id=current_user.active_company_id,
            actor_user_id=current_user.user_id,
            name=payload.name,
            description=payload.description,
            logo_document_id=payload.logo_document_id,
        )
    )
    db.commit()
    db.refresh(brand)
    return BrandOut.model_validate(brand)


@router.get("/brands/{brand_id}", response_model=BrandOut)
def get_brand(
    brand_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("catalog:brands:read")),
) -> BrandOut:
    repo = BrandRepository(db)
    brand = repo.get(company_id=current_user.active_company_id, brand_id=brand_id)
    if brand is None:
        raise NotFoundError("Brand not found")
    return BrandOut.model_validate(brand)


@router.patch("/brands/{brand_id}", response_model=BrandOut)
def update_brand(
    brand_id: uuid.UUID,
    payload: BrandUpdate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("catalog:brands:write")),
) -> BrandOut:
    use_case = UpdateBrandUseCase(db)
    brand = use_case.execute(
        UpdateBrandInput(
            company_id=current_user.active_company_id,
            actor_user_id=current_user.user_id,
            brand_id=brand_id,
            name=payload.name,
            description=payload.description,
            logo_document_id=payload.logo_document_id,
            status=payload.status,
        )
    )
    db.commit()
    db.refresh(brand)
    return BrandOut.model_validate(brand)
