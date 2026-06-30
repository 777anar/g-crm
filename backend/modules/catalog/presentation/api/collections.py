import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from core.api.errors import NotFoundError
from core.db.session import get_db
from core.rbac.dependencies import CurrentUser, require_permission
from modules.catalog.application.dtos import CreateCollectionInput, UpdateCollectionInput
from modules.catalog.application.use_cases import CreateCollectionUseCase, UpdateCollectionUseCase
from modules.catalog.infrastructure.repositories.collection_repository import CollectionRepository
from modules.catalog.presentation.schemas.collection import (
    CollectionCreate,
    CollectionListOut,
    CollectionOut,
    CollectionUpdate,
)

router = APIRouter()


@router.get("/collections", response_model=CollectionListOut)
def list_collections(
    brand_id: Optional[uuid.UUID] = Query(default=None),
    include_hidden: bool = Query(default=False),
    search: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("catalog:collections:read")),
) -> CollectionListOut:
    repo = CollectionRepository(db)
    items = repo.list(
        company_id=current_user.active_company_id, brand_id=brand_id, include_hidden=include_hidden, search=search
    )
    return CollectionListOut(items=[CollectionOut.model_validate(c) for c in items])


@router.post("/collections", response_model=CollectionOut)
def create_collection(
    payload: CollectionCreate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("catalog:collections:write")),
) -> CollectionOut:
    use_case = CreateCollectionUseCase(db)
    collection = use_case.execute(
        CreateCollectionInput(
            company_id=current_user.active_company_id,
            actor_user_id=current_user.user_id,
            brand_id=payload.brand_id,
            name=payload.name,
            description=payload.description,
        )
    )
    db.commit()
    db.refresh(collection)
    return CollectionOut.model_validate(collection)


@router.get("/collections/{collection_id}", response_model=CollectionOut)
def get_collection(
    collection_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("catalog:collections:read")),
) -> CollectionOut:
    repo = CollectionRepository(db)
    collection = repo.get(company_id=current_user.active_company_id, collection_id=collection_id)
    if collection is None:
        raise NotFoundError("Collection not found")
    return CollectionOut.model_validate(collection)


@router.patch("/collections/{collection_id}", response_model=CollectionOut)
def update_collection(
    collection_id: uuid.UUID,
    payload: CollectionUpdate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("catalog:collections:write")),
) -> CollectionOut:
    use_case = UpdateCollectionUseCase(db)
    collection = use_case.execute(
        UpdateCollectionInput(
            company_id=current_user.active_company_id,
            actor_user_id=current_user.user_id,
            collection_id=collection_id,
            name=payload.name,
            description=payload.description,
            status=payload.status,
        )
    )
    db.commit()
    db.refresh(collection)
    return CollectionOut.model_validate(collection)
