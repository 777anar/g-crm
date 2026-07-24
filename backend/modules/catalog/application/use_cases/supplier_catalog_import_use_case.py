"""Standardized supplier catalog import (Phase 20: Advanced Cut
Optimization & Supply Chain Intelligence). Sprint 2 (Phase 9) deliberately
kept Brand/Stone/Thickness/Size as free-text-backed curated suggestions
rather than real manufacturer spec-sheet data, explicitly deferring a real
import pipeline -- this is that follow-through: a real CSV import that
finds-or-creates Brands and upserts Materials/Thicknesses/Sizes from
supplier-provided rows, instead of every option being typed in by hand.

Best-effort, per-row: one bad row (a missing brand name, whatever) is
recorded as an error and skipped, not an all-or-nothing transaction --
consistent with this being a bulk import, where a partial success that
tells the user exactly which rows to fix is far more useful than an
all-or-nothing failure on row 47 of 300."""
import uuid
from dataclasses import dataclass, field
from typing import List

from sqlalchemy.orm import Session

from core.audit.service import record_audit
from core.events.event_bus import event_bus
from core.events.event_envelope import Event
from modules.catalog.application.dtos import ImportSupplierCatalogInput, SupplierCatalogRowInput
from modules.catalog.domain import events as catalog_events
from modules.catalog.domain.value_objects import DEFAULT_ENTITY_STATUS, DEFAULT_MATERIAL_STATUS
from modules.catalog.infrastructure.models.brand import Brand
from modules.catalog.infrastructure.models.material import StoneMaterial
from modules.catalog.infrastructure.models.material_size import MaterialSize
from modules.catalog.infrastructure.models.material_thickness import MaterialThickness
from modules.catalog.infrastructure.repositories.brand_repository import BrandRepository
from modules.catalog.infrastructure.repositories.material_option_repository import (
    MaterialSizeRepository,
    MaterialThicknessRepository,
)
from modules.catalog.infrastructure.repositories.material_repository import MaterialRepository

MODULE_NAME = "catalog"

_UPDATABLE_FIELDS = ("material_type", "color", "finish", "country_of_origin", "description")


@dataclass
class RowError:
    row_number: int
    message: str


@dataclass
class ImportSummary:
    brands_created: int = 0
    materials_created: int = 0
    materials_updated: int = 0
    thicknesses_added: int = 0
    sizes_added: int = 0
    errors: List[RowError] = field(default_factory=list)


class ImportSupplierCatalogUseCase:
    def __init__(self, db: Session):
        self.db = db
        self.brands = BrandRepository(db)
        self.materials = MaterialRepository(db)
        self.thicknesses = MaterialThicknessRepository(db)
        self.sizes = MaterialSizeRepository(db)

    def execute(self, data: ImportSupplierCatalogInput) -> ImportSummary:
        summary = ImportSummary()
        for row_number, row in enumerate(data.rows, start=1):
            try:
                self._process_row(data.company_id, data.actor_user_id, row, summary)
            except Exception as exc:  # noqa: BLE001 -- a bad row must not abort the whole import
                summary.errors.append(RowError(row_number=row_number, message=str(exc)))
        self.db.flush()
        return summary

    def _process_row(self, company_id: uuid.UUID, actor_user_id: uuid.UUID, row: SupplierCatalogRowInput, summary: ImportSummary) -> None:
        brand_name = (row.brand_name or "").strip()
        material_name = (row.material_name or "").strip()
        if not brand_name:
            raise ValueError("brand is required")
        if not material_name:
            raise ValueError("material_name is required")

        brand = self.brands.get_by_name(company_id=company_id, name=brand_name)
        if brand is None:
            brand = Brand(company_id=company_id, name=brand_name, status=DEFAULT_ENTITY_STATUS, created_by=actor_user_id)
            self.brands.add(brand)
            summary.brands_created += 1
            event_bus.publish(
                Event(
                    name=catalog_events.BRAND_CREATED,
                    company_id=company_id,
                    payload={"brand_id": str(brand.id), "name": brand.name},
                    published_by_module=MODULE_NAME,
                ),
                self.db,
            )

        material = self.materials.get_by_brand_and_name(company_id=company_id, brand_id=brand.id, name=material_name)
        created = material is None
        if created:
            material = StoneMaterial(
                company_id=company_id,
                brand_id=brand.id,
                name=material_name,
                material_type=row.material_type,
                color=row.color,
                finish=row.finish,
                country_of_origin=row.country_of_origin,
                description=row.description,
                status=DEFAULT_MATERIAL_STATUS,
                created_by=actor_user_id,
            )
            self.materials.add(material)
            summary.materials_created += 1
        else:
            changed = False
            for field_name in _UPDATABLE_FIELDS:
                new_value = getattr(row, field_name)
                if new_value:
                    setattr(material, field_name, new_value)
                    changed = True
            if changed:
                summary.materials_updated += 1
            self.db.flush()

        record_audit(
            self.db,
            company_id=company_id,
            module=MODULE_NAME,
            actor_user_id=actor_user_id,
            action="material.created" if created else "material.updated",
            entity_type="material",
            entity_id=material.id,
            diff={"source": "supplier_catalog_import", "brand": brand_name, "name": material_name},
        )
        event_bus.publish(
            Event(
                name=catalog_events.MATERIAL_CREATED if created else catalog_events.MATERIAL_UPDATED,
                company_id=company_id,
                payload={"material_id": str(material.id), "name": material.name, "brand_id": str(brand.id)},
                published_by_module=MODULE_NAME,
            ),
            self.db,
        )

        existing_thicknesses = {
            t.thickness_mm for t in self.thicknesses.list_for_material(company_id=company_id, material_id=material.id)
        }
        for i, thickness_mm in enumerate(row.thicknesses_mm):
            value = thickness_mm.strip()
            if value and value not in existing_thicknesses:
                self.thicknesses.add(MaterialThickness(
                    company_id=company_id, material_id=material.id, thickness_mm=value, sort_order=i,
                ))
                existing_thicknesses.add(value)
                summary.thicknesses_added += 1

        existing_sizes = {
            s.dimensions for s in self.sizes.list_for_material(company_id=company_id, material_id=material.id)
        }
        for i, dimensions in enumerate(row.sizes):
            value = dimensions.strip()
            if value and value not in existing_sizes:
                self.sizes.add(MaterialSize(
                    company_id=company_id, material_id=material.id, dimensions=value, sort_order=i,
                ))
                existing_sizes.add(value)
                summary.sizes_added += 1
