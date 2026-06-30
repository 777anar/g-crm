"""Application-layer input DTOs. Presentation schemas (Pydantic) map onto
these before calling a use-case, keeping the use-case layer free of any
FastAPI/Pydantic import -- same pattern as modules/crm."""
import uuid
from dataclasses import dataclass
from decimal import Decimal
from typing import Optional


@dataclass
class ActorContext:
    company_id: uuid.UUID
    actor_user_id: uuid.UUID


@dataclass
class CreateBrandInput(ActorContext):
    name: str
    description: Optional[str] = None
    logo_document_id: Optional[uuid.UUID] = None


@dataclass
class UpdateBrandInput(ActorContext):
    brand_id: uuid.UUID
    name: Optional[str] = None
    description: Optional[str] = None
    logo_document_id: Optional[uuid.UUID] = None
    status: Optional[str] = None


@dataclass
class CreateCollectionInput(ActorContext):
    brand_id: uuid.UUID
    name: str
    description: Optional[str] = None


@dataclass
class UpdateCollectionInput(ActorContext):
    collection_id: uuid.UUID
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None


@dataclass
class CreateMaterialInput(ActorContext):
    brand_id: uuid.UUID
    name: str
    collection_id: Optional[uuid.UUID] = None
    material_type: Optional[str] = None
    color: Optional[str] = None
    finish: Optional[str] = None
    thickness_mm: Optional[str] = None
    dimensions: Optional[str] = None
    country_of_origin: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None


@dataclass
class UpdateMaterialInput(ActorContext):
    material_id: uuid.UUID
    brand_id: Optional[uuid.UUID] = None
    collection_id: Optional[uuid.UUID] = None
    name: Optional[str] = None
    material_type: Optional[str] = None
    color: Optional[str] = None
    finish: Optional[str] = None
    thickness_mm: Optional[str] = None
    dimensions: Optional[str] = None
    country_of_origin: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None


@dataclass
class CreateWarehouseInput(ActorContext):
    name: str
    address: Optional[str] = None


@dataclass
class UpdateWarehouseInput(ActorContext):
    warehouse_id: uuid.UUID
    name: Optional[str] = None
    address: Optional[str] = None
    status: Optional[str] = None


@dataclass
class CreateSlabInput(ActorContext):
    material_id: uuid.UUID
    warehouse_id: uuid.UUID
    slab_number: str
    lot_number: Optional[str] = None
    barcode: Optional[str] = None
    rack_location: Optional[str] = None
    length_mm: Optional[Decimal] = None
    width_mm: Optional[Decimal] = None
    weight_kg: Optional[Decimal] = None
    status: Optional[str] = None


@dataclass
class UpdateSlabStatusInput(ActorContext):
    slab_id: uuid.UUID
    status: str


@dataclass
class CreatePriceListInput(ActorContext):
    name: str
    currency: str = "AZN"
    is_default: bool = False


@dataclass
class UpsertPriceListEntryInput(ActorContext):
    price_list_id: uuid.UUID
    material_id: uuid.UUID
    cost_price: Decimal = Decimal("0")
    sale_price: Decimal = Decimal("0")


@dataclass
class AddMaterialImageInput(ActorContext):
    material_id: uuid.UUID
    document_id: uuid.UUID
    image_type: str = "gallery"
    sort_order: int = 0


@dataclass
class AddMaterialDocumentInput(ActorContext):
    material_id: uuid.UUID
    document_id: uuid.UUID
    document_type: str = "technical_pdf"
