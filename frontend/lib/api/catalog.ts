import { apiDownload, apiRequest } from "../api-client";
import type {
  Attachment,
  Brand,
  Collection,
  EntityStatus,
  Material,
  MaterialDocumentAsset,
  MaterialImage,
  MaterialSize,
  MaterialStatus,
  MaterialThickness,
  Paginated,
  PriceList,
  PriceListEntry,
  ReservationStatus,
  Slab,
  SlabReservation,
  SlabStatus,
  SupplierCatalogImportSummary,
  Warehouse,
} from "../types";

// --- Brands ------------------------------------------------------------

export function listBrands(
  params: { includeHidden?: boolean; search?: string; limit?: number; cursor?: string } = {}
) {
  return apiRequest<Paginated<Brand>>("/api/v1/catalog/brands", {
    searchParams: {
      include_hidden: params.includeHidden,
      search: params.search || undefined,
      limit: params.limit,
      cursor: params.cursor,
    },
  });
}

export function getBrand(id: string) {
  return apiRequest<Brand>(`/api/v1/catalog/brands/${id}`);
}

export function createBrand(input: { name: string; description?: string }) {
  return apiRequest<Brand>("/api/v1/catalog/brands", { method: "POST", body: input });
}

export function updateBrand(id: string, input: { name?: string; description?: string; status?: EntityStatus }) {
  return apiRequest<Brand>(`/api/v1/catalog/brands/${id}`, { method: "PATCH", body: input });
}

// --- Collections ---------------------------------------------------------

export function listCollections(params: { brandId?: string; includeHidden?: boolean; search?: string } = {}) {
  return apiRequest<{ items: Collection[] }>("/api/v1/catalog/collections", {
    searchParams: { brand_id: params.brandId, include_hidden: params.includeHidden, search: params.search || undefined },
  });
}

export function createCollection(input: { brand_id: string; name: string; description?: string }) {
  return apiRequest<Collection>("/api/v1/catalog/collections", { method: "POST", body: input });
}

export function updateCollection(id: string, input: { name?: string; description?: string; status?: EntityStatus }) {
  return apiRequest<Collection>(`/api/v1/catalog/collections/${id}`, { method: "PATCH", body: input });
}

// --- Materials -------------------------------------------------------------

export function listMaterials(
  params: {
    brandId?: string;
    collectionId?: string;
    status?: MaterialStatus;
    search?: string;
    sort?: string;
    limit?: number;
    cursor?: string;
  } = {}
) {
  return apiRequest<Paginated<Material>>("/api/v1/catalog/materials", {
    searchParams: {
      brand_id: params.brandId,
      collection_id: params.collectionId,
      status: params.status,
      search: params.search || undefined,
      sort: params.sort,
      limit: params.limit,
      cursor: params.cursor,
    },
  });
}

export function getMaterial(id: string) {
  return apiRequest<Material>(`/api/v1/catalog/materials/${id}`);
}

export type CreateMaterialInput = {
  brand_id: string;
  collection_id?: string;
  name: string;
  material_type?: string;
  color?: string;
  finish?: string;
  thickness_mm?: string;
  dimensions?: string;
  country_of_origin?: string;
  description?: string;
  status?: MaterialStatus;
};

export function createMaterial(input: CreateMaterialInput) {
  return apiRequest<Material>("/api/v1/catalog/materials", { method: "POST", body: input });
}

export function updateMaterial(id: string, input: Partial<CreateMaterialInput>) {
  return apiRequest<Material>(`/api/v1/catalog/materials/${id}`, { method: "PATCH", body: input });
}

export function listMaterialImages(materialId: string) {
  return apiRequest<{ items: MaterialImage[] }>(`/api/v1/catalog/materials/${materialId}/images`);
}

export function addMaterialImage(materialId: string, input: { document_id: string; image_type: string; sort_order?: number }) {
  return apiRequest<MaterialImage>(`/api/v1/catalog/materials/${materialId}/images`, { method: "POST", body: input });
}

export function listMaterialDocuments(materialId: string) {
  return apiRequest<{ items: MaterialDocumentAsset[] }>(`/api/v1/catalog/materials/${materialId}/documents`);
}

export function addMaterialDocument(materialId: string, input: { document_id: string; document_type: string }) {
  return apiRequest<MaterialDocumentAsset>(`/api/v1/catalog/materials/${materialId}/documents`, {
    method: "POST",
    body: input,
  });
}

export function uploadMaterialAsset(materialId: string, file: File) {
  const formData = new FormData();
  formData.append("module", "catalog");
  formData.append("related_entity_type", "material");
  formData.append("related_entity_id", materialId);
  formData.append("file", file);
  return apiRequest<Attachment>("/api/v1/core/documents", { method: "POST", formData });
}

export function listPricesForMaterial(materialId: string) {
  return apiRequest<{ items: PriceListEntry[] }>(`/api/v1/catalog/materials/${materialId}/prices`);
}

// --- Standardized supplier catalog import (Phase 20) --------------------

export function downloadSupplierCatalogImportTemplate() {
  return apiDownload("/api/v1/catalog/materials/import/template", {
    filename: "supplier_catalog_import_template.csv",
  });
}

export function importSupplierCatalog(file: File) {
  const formData = new FormData();
  formData.append("file", file);
  return apiRequest<SupplierCatalogImportSummary>("/api/v1/catalog/materials/import", {
    method: "POST",
    formData,
  });
}

// --- Material Thickness/Size options (Sprint 4) -------------------------

export function listMaterialThicknesses(materialId: string) {
  return apiRequest<{ items: MaterialThickness[] }>(`/api/v1/catalog/materials/${materialId}/thicknesses`);
}

export function addMaterialThickness(materialId: string, input: { thickness_mm: string; sort_order?: number }) {
  return apiRequest<MaterialThickness>(`/api/v1/catalog/materials/${materialId}/thicknesses`, {
    method: "POST",
    body: input,
  });
}

export function deleteMaterialThickness(id: string) {
  return apiRequest<void>(`/api/v1/catalog/material-thicknesses/${id}`, { method: "DELETE" });
}

export function listMaterialSizes(materialId: string) {
  return apiRequest<{ items: MaterialSize[] }>(`/api/v1/catalog/materials/${materialId}/sizes`);
}

export function addMaterialSize(materialId: string, input: { dimensions: string; sort_order?: number }) {
  return apiRequest<MaterialSize>(`/api/v1/catalog/materials/${materialId}/sizes`, {
    method: "POST",
    body: input,
  });
}

export function deleteMaterialSize(id: string) {
  return apiRequest<void>(`/api/v1/catalog/material-sizes/${id}`, { method: "DELETE" });
}

// --- Warehouses --------------------------------------------------------

export function listWarehouses(params: { includeHidden?: boolean } = {}) {
  return apiRequest<{ items: Warehouse[] }>("/api/v1/catalog/warehouses", {
    searchParams: { include_hidden: params.includeHidden },
  });
}

export function createWarehouse(input: { name: string; address?: string }) {
  return apiRequest<Warehouse>("/api/v1/catalog/warehouses", { method: "POST", body: input });
}

export function updateWarehouse(id: string, input: { name?: string; address?: string; status?: EntityStatus }) {
  return apiRequest<Warehouse>(`/api/v1/catalog/warehouses/${id}`, { method: "PATCH", body: input });
}

// --- Slabs ---------------------------------------------------------------

export function listSlabs(
  params: {
    materialId?: string;
    warehouseId?: string;
    status?: SlabStatus;
    search?: string;
    sort?: string;
    limit?: number;
    cursor?: string;
  } = {}
) {
  return apiRequest<Paginated<Slab>>("/api/v1/catalog/slabs", {
    searchParams: {
      material_id: params.materialId,
      warehouse_id: params.warehouseId,
      status: params.status,
      search: params.search || undefined,
      sort: params.sort,
      limit: params.limit,
      cursor: params.cursor,
    },
  });
}

export type CreateSlabInput = {
  material_id: string;
  warehouse_id: string;
  slab_number: string;
  lot_number?: string;
  barcode?: string;
  rack_location?: string;
  length_mm?: string;
  width_mm?: string;
  weight_kg?: string;
  status?: SlabStatus;
};

export function createSlab(input: CreateSlabInput) {
  return apiRequest<Slab>("/api/v1/catalog/slabs", { method: "POST", body: input });
}

export function updateSlabStatus(id: string, status: SlabStatus) {
  return apiRequest<Slab>(`/api/v1/catalog/slabs/${id}/status`, { method: "PATCH", body: { status } });
}

// --- Material Reservation (Phase 1: Stone Fabrication Workflow) ----------

export function listSlabReservations(slabId: string) {
  return apiRequest<{ items: SlabReservation[] }>(`/api/v1/catalog/slabs/${slabId}/reservations`);
}

export function reserveSlab(
  slabId: string,
  input: { order_id: string; order_item_id: string; notes?: string }
) {
  return apiRequest<SlabReservation>(`/api/v1/catalog/slabs/${slabId}/reserve`, { method: "POST", body: input });
}

export function releaseSlabReservation(reservationId: string) {
  return apiRequest<SlabReservation>(`/api/v1/catalog/slabs/reservations/${reservationId}/release`, {
    method: "POST",
  });
}

export function listReservationsForOrder(orderId: string) {
  return apiRequest<{ items: SlabReservation[] }>("/api/v1/catalog/reservations", {
    searchParams: { order_id: orderId },
  });
}

/** Company-wide reservation browsing (Phase 19) -- `order_id` omitted lists
 * every active-or-not reservation across the company, cursor-paginated, so
 * staff can manage reservations directly instead of only reaching them by
 * already knowing which order to look at. */
export function listReservations(
  params: { orderId?: string; status?: ReservationStatus; limit?: number; cursor?: string } = {}
) {
  return apiRequest<Paginated<SlabReservation>>("/api/v1/catalog/reservations", {
    searchParams: {
      order_id: params.orderId,
      status: params.status,
      limit: params.limit,
      cursor: params.cursor,
    },
  });
}

export function createOffcut(
  slabId: string,
  input: { warehouse_id: string; slab_number: string; length_mm?: string; width_mm?: string; weight_kg?: string; notes?: string }
) {
  return apiRequest<Slab>(`/api/v1/catalog/slabs/${slabId}/offcuts`, { method: "POST", body: input });
}

// --- Offcut Library (Phase 2) ---------------------------------------------

export function searchOffcuts(
  params: {
    materialId?: string;
    thicknessMm?: string;
    finish?: string;
    warehouseId?: string;
    minLengthMm?: string;
    minWidthMm?: string;
    minAreaM2?: string;
    search?: string;
    limit?: number;
  } = {}
) {
  return apiRequest<{ items: Slab[] }>("/api/v1/catalog/slabs/offcuts", {
    searchParams: {
      material_id: params.materialId,
      thickness_mm: params.thicknessMm,
      finish: params.finish,
      warehouse_id: params.warehouseId,
      min_length_mm: params.minLengthMm,
      min_width_mm: params.minWidthMm,
      min_area_m2: params.minAreaM2,
      search: params.search || undefined,
      limit: params.limit,
    },
  });
}

// --- Price Lists ---------------------------------------------------------

export function listPriceLists(params: { includeHidden?: boolean } = {}) {
  return apiRequest<{ items: PriceList[] }>("/api/v1/catalog/price-lists", {
    searchParams: { include_hidden: params.includeHidden },
  });
}

export function createPriceList(input: { name: string; currency?: string; is_default?: boolean }) {
  return apiRequest<PriceList>("/api/v1/catalog/price-lists", { method: "POST", body: input });
}

export function listPriceListEntries(priceListId: string) {
  return apiRequest<{ items: PriceListEntry[] }>(`/api/v1/catalog/price-lists/${priceListId}/entries`);
}

export function upsertPriceListEntry(
  priceListId: string,
  input: { material_id: string; cost_price: string; sale_price: string }
) {
  return apiRequest<PriceListEntry>(`/api/v1/catalog/price-lists/${priceListId}/entries`, {
    method: "PUT",
    body: input,
  });
}
