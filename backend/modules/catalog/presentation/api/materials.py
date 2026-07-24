import csv
import io
import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, File, Query, UploadFile
from fastapi.responses import Response
from sqlalchemy.orm import Session

from core.api.errors import NotFoundError, ValidationAPIError
from core.api.pagination import decode_cursor, encode_cursor
from core.db.session import get_db
from core.rbac.dependencies import CurrentUser, require_permission
from modules.catalog.application.dtos import (
    AddMaterialDocumentInput,
    AddMaterialImageInput,
    AddMaterialSizeInput,
    AddMaterialThicknessInput,
    CreateMaterialInput,
    ImportSupplierCatalogInput,
    SupplierCatalogRowInput,
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
    ImportSupplierCatalogUseCase,
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
    SupplierCatalogImportSummaryOut,
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


# ── Standardized supplier catalog import (Phase 20) ───────────────────────────

_IMPORT_TEMPLATE_CSV = (
    "brand,material_name,material_type,color,finish,country_of_origin,description,thicknesses_mm,sizes\n"
    'NEOLITH,Calacatta Gold,Sintered Stone,White,Polished,Spain,"Elegant marble-look surface",'
    '"12;20;30","3200x1600mm;3000x1400mm"\n'
)

def _split_multi(value: Optional[str]) -> List[str]:
    if not value:
        return []
    return [v.strip() for v in value.split(";") if v.strip()]


@router.get("/materials/import/template")
def download_supplier_catalog_import_template(
    current_user: CurrentUser = Depends(require_permission("catalog:materials:read")),
) -> Response:
    content = ("﻿" + _IMPORT_TEMPLATE_CSV).encode("utf-8")
    return Response(
        content=content,
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="supplier_catalog_import_template.csv"'},
    )


@router.post("/materials/import", response_model=SupplierCatalogImportSummaryOut)
async def import_supplier_catalog(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("catalog:materials:write")),
) -> SupplierCatalogImportSummaryOut:
    """A real CSV import pipeline for supplier catalogs (Phase 20) --
    Brand/Stone/Thickness/Size options sourced from a supplier's own data
    instead of typed in by hand (Sprint 2's deliberately-deferred scope,
    `MASTER_DEVELOPMENT_ROADMAP.md` Phase 20). One row per material;
    `thicknesses_mm`/`sizes` are semicolon-separated lists appended to
    that material's existing option lists. Best-effort per row -- see
    `ImportSupplierCatalogUseCase`'s docstring for why this isn't one
    all-or-nothing transaction."""
    raw = await file.read()
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValidationAPIError(
            "File is not valid UTF-8 text", details=[{"field": "file", "issue": "invalid encoding"}]
        ) from exc

    reader = csv.DictReader(io.StringIO(text))
    missing_columns = [c for c in ("brand", "material_name") if c not in (reader.fieldnames or [])]
    if missing_columns:
        raise ValidationAPIError(
            f"CSV is missing required column(s): {', '.join(missing_columns)}",
            details=[{"field": "file", "issue": "missing required columns"}],
        )

    rows = [
        SupplierCatalogRowInput(
            brand_name=r.get("brand", ""),
            material_name=r.get("material_name", ""),
            material_type=r.get("material_type") or None,
            color=r.get("color") or None,
            finish=r.get("finish") or None,
            country_of_origin=r.get("country_of_origin") or None,
            description=r.get("description") or None,
            thicknesses_mm=_split_multi(r.get("thicknesses_mm")),
            sizes=_split_multi(r.get("sizes")),
        )
        for r in reader
    ]

    use_case = ImportSupplierCatalogUseCase(db)
    summary = use_case.execute(
        ImportSupplierCatalogInput(
            company_id=current_user.active_company_id, actor_user_id=current_user.user_id, rows=rows,
        )
    )
    db.commit()
    return SupplierCatalogImportSummaryOut(
        brands_created=summary.brands_created,
        materials_created=summary.materials_created,
        materials_updated=summary.materials_updated,
        thicknesses_added=summary.thicknesses_added,
        sizes_added=summary.sizes_added,
        errors=[{"row_number": e.row_number, "message": e.message} for e in summary.errors],
    )
