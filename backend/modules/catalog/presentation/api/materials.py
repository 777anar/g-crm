import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from core.api.errors import NotFoundError
from core.api.pagination import decode_cursor, encode_cursor
from core.db.session import get_db
from core.rbac.dependencies import CurrentUser, require_permission
from modules.catalog.application.dtos import (
    AddMaterialDocumentInput,
    AddMaterialImageInput,
    AddMaterialSizeInput,
    AddMaterialThicknessInput,
    CreateMaterialInput,
    UpdateMaterialInput,
)
from modules.catalog.application.use_cases import (
    AddMaterialDocumentUseCase,
    AddMaterialImageUseCase,
    AddMaterialSizeUseCase,
    AddMaterialThicknessUseCase,
    CreateMaterialUseCase,
    DeleteMaterialSizeUseCase,
    DeleteMaterialThicknessUseCase,
    UpdateMaterialUseCase,
)
from modules.catalog.infrastructure.repositories.material_asset_repository import (
    MaterialDocumentRepository,
    MaterialImageRepository,
)
from modules.catalog.infrastructure.repositories.material_option_repository import (
    MaterialSizeRepository,
    MaterialThicknessRepository,
)
from modules.catalog.infrastructure.repositories.material_repository import MaterialRepository
from modules.catalog.presentation.schemas.material import (
    MaterialCreate,
    MaterialListOut,
    MaterialOut,
    MaterialUpdate,
)
from modules.catalog.presentation.schemas.material_asset import (
    MaterialDocumentCreate,
    MaterialDocumentListOut,
    MaterialDocumentOut,
    MaterialImageCreate,
    MaterialImageListOut,
    MaterialImageOut,
)
from modules.catalog.presentation.schemas.material_option import (
    MaterialSizeCreate,
    MaterialSizeListOut,
    MaterialSizeOut,
    MaterialThicknessCreate,
    MaterialThicknessListOut,
    MaterialThicknessOut,
)

router = APIRouter()


@router.get("/materials", response_model=MaterialListOut)
def list_materials(
    brand_id: Optional[uuid.UUID] = Query(default=None),
    collection_id: Optional[uuid.UUID] = Query(default=None),
    status: Optional[str] = Query(default=None),
    search: Optional[str] = Query(default=None),
    sort: Optional[str] = Query(default=None),
    limit: int = Query(default=25, le=100),
    cursor: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("catalog:materials:read")),
) -> MaterialListOut:
    repo = MaterialRepository(db)
    offset = decode_cursor(cursor)
    items = repo.list(
        company_id=current_user.active_company_id,
        brand_id=brand_id,
        collection_id=collection_id,
        status=status,
        search=search,
        sort=sort,
        limit=limit + 1,
        offset=offset,
    )
    has_more = len(items) > limit
    page = items[:limit]
    next_cursor = encode_cursor(offset=offset + limit) if has_more else None
    return MaterialListOut(items=[MaterialOut.model_validate(m) for m in page], next_cursor=next_cursor)


@router.post("/materials", response_model=MaterialOut)
def create_material(
    payload: MaterialCreate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("catalog:materials:write")),
) -> MaterialOut:
    use_case = CreateMaterialUseCase(db)
    material = use_case.execute(
        CreateMaterialInput(
            company_id=current_user.active_company_id,
            actor_user_id=current_user.user_id,
            brand_id=payload.brand_id,
            collection_id=payload.collection_id,
            name=payload.name,
            material_type=payload.material_type,
            color=payload.color,
            finish=payload.finish,
            thickness_mm=payload.thickness_mm,
            dimensions=payload.dimensions,
            country_of_origin=payload.country_of_origin,
            description=payload.description,
            status=payload.status,
        )
    )
    db.commit()
    db.refresh(material)
    return MaterialOut.model_validate(material)


@router.get("/materials/{material_id}", response_model=MaterialOut)
def get_material(
    material_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("catalog:materials:read")),
) -> MaterialOut:
    repo = MaterialRepository(db)
    material = repo.get(company_id=current_user.active_company_id, material_id=material_id)
    if material is None:
        raise NotFoundError("Material not found")
    return MaterialOut.model_validate(material)


@router.patch("/materials/{material_id}", response_model=MaterialOut)
def update_material(
    material_id: uuid.UUID,
    payload: MaterialUpdate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("catalog:materials:write")),
) -> MaterialOut:
    use_case = UpdateMaterialUseCase(db)
    material = use_case.execute(
        UpdateMaterialInput(
            company_id=current_user.active_company_id,
            actor_user_id=current_user.user_id,
            material_id=material_id,
            brand_id=payload.brand_id,
            collection_id=payload.collection_id,
            name=payload.name,
            material_type=payload.material_type,
            color=payload.color,
            finish=payload.finish,
            thickness_mm=payload.thickness_mm,
            dimensions=payload.dimensions,
            country_of_origin=payload.country_of_origin,
            description=payload.description,
            status=payload.status,
        )
    )
    db.commit()
    db.refresh(material)
    return MaterialOut.model_validate(material)


@router.get("/materials/{material_id}/images", response_model=MaterialImageListOut)
def list_material_images(
    material_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("catalog:materials:read")),
) -> MaterialImageListOut:
    repo = MaterialImageRepository(db)
    items = repo.list_for_material(company_id=current_user.active_company_id, material_id=material_id)
    return MaterialImageListOut(items=[MaterialImageOut.model_validate(i) for i in items])


@router.post("/materials/{material_id}/images", response_model=MaterialImageOut)
def add_material_image(
    material_id: uuid.UUID,
    payload: MaterialImageCreate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("catalog:materials:write")),
) -> MaterialImageOut:
    use_case = AddMaterialImageUseCase(db)
    image = use_case.execute(
        AddMaterialImageInput(
            company_id=current_user.active_company_id,
            actor_user_id=current_user.user_id,
            material_id=material_id,
            document_id=payload.document_id,
            image_type=payload.image_type,
            sort_order=payload.sort_order,
        )
    )
    db.commit()
    db.refresh(image)
    return MaterialImageOut.model_validate(image)


@router.get("/materials/{material_id}/documents", response_model=MaterialDocumentListOut)
def list_material_documents(
    material_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("catalog:materials:read")),
) -> MaterialDocumentListOut:
    repo = MaterialDocumentRepository(db)
    items = repo.list_for_material(company_id=current_user.active_company_id, material_id=material_id)
    return MaterialDocumentListOut(items=[MaterialDocumentOut.model_validate(d) for d in items])


@router.post("/materials/{material_id}/documents", response_model=MaterialDocumentOut)
def add_material_document(
    material_id: uuid.UUID,
    payload: MaterialDocumentCreate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("catalog:materials:write")),
) -> MaterialDocumentOut:
    use_case = AddMaterialDocumentUseCase(db)
    material_document = use_case.execute(
        AddMaterialDocumentInput(
            company_id=current_user.active_company_id,
            actor_user_id=current_user.user_id,
            material_id=material_id,
            document_id=payload.document_id,
            document_type=payload.document_type,
        )
    )
    db.commit()
    db.refresh(material_document)
    return MaterialDocumentOut.model_validate(material_document)


@router.get("/materials/{material_id}/thicknesses", response_model=MaterialThicknessListOut)
def list_material_thicknesses(
    material_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("catalog:materials:read")),
) -> MaterialThicknessListOut:
    repo = MaterialThicknessRepository(db)
    items = repo.list_for_material(company_id=current_user.active_company_id, material_id=material_id)
    return MaterialThicknessListOut(items=[MaterialThicknessOut.model_validate(t) for t in items])


@router.post("/materials/{material_id}/thicknesses", response_model=MaterialThicknessOut)
def add_material_thickness(
    material_id: uuid.UUID,
    payload: MaterialThicknessCreate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("catalog:materials:write")),
) -> MaterialThicknessOut:
    use_case = AddMaterialThicknessUseCase(db)
    thickness = use_case.execute(
        AddMaterialThicknessInput(
            company_id=current_user.active_company_id,
            actor_user_id=current_user.user_id,
            material_id=material_id,
            thickness_mm=payload.thickness_mm,
            sort_order=payload.sort_order,
        )
    )
    db.commit()
    db.refresh(thickness)
    return MaterialThicknessOut.model_validate(thickness)


@router.delete("/material-thicknesses/{thickness_id}", status_code=204)
def delete_material_thickness(
    thickness_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("catalog:materials:write")),
) -> None:
    use_case = DeleteMaterialThicknessUseCase(db)
    use_case.execute(
        company_id=current_user.active_company_id,
        actor_user_id=current_user.user_id,
        thickness_id=thickness_id,
    )
    db.commit()


@router.get("/materials/{material_id}/sizes", response_model=MaterialSizeListOut)
def list_material_sizes(
    material_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("catalog:materials:read")),
) -> MaterialSizeListOut:
    repo = MaterialSizeRepository(db)
    items = repo.list_for_material(company_id=current_user.active_company_id, material_id=material_id)
    return MaterialSizeListOut(items=[MaterialSizeOut.model_validate(s) for s in items])


@router.post("/materials/{material_id}/sizes", response_model=MaterialSizeOut)
def add_material_size(
    material_id: uuid.UUID,
    payload: MaterialSizeCreate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("catalog:materials:write")),
) -> MaterialSizeOut:
    use_case = AddMaterialSizeUseCase(db)
    size = use_case.execute(
        AddMaterialSizeInput(
            company_id=current_user.active_company_id,
            actor_user_id=current_user.user_id,
            material_id=material_id,
            dimensions=payload.dimensions,
            sort_order=payload.sort_order,
        )
    )
    db.commit()
    db.refresh(size)
    return MaterialSizeOut.model_validate(size)


@router.delete("/material-sizes/{size_id}", status_code=204)
def delete_material_size(
    size_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("catalog:materials:write")),
) -> None:
    use_case = DeleteMaterialSizeUseCase(db)
    use_case.execute(
        company_id=current_user.active_company_id,
        actor_user_id=current_user.user_id,
        size_id=size_id,
    )
    db.commit()
