"""Domain events the Stone Catalog module publishes. Authoritative
definitions per the frozen EDA architecture -- other modules (Sales,
Production) subscribe to these names without importing Catalog's code.
The future Sales module is expected to subscribe to SLAB_RESERVED /
SLAB_SOLD when a Quote/Order references a specific slab."""

BRAND_CREATED = "BrandCreated"
COLLECTION_CREATED = "CollectionCreated"
MATERIAL_CREATED = "MaterialCreated"
MATERIAL_UPDATED = "MaterialUpdated"
WAREHOUSE_CREATED = "WarehouseCreated"
SLAB_CREATED = "SlabCreated"
SLAB_STATUS_CHANGED = "SlabStatusChanged"
PRICE_LIST_CREATED = "PriceListCreated"
PRICE_LIST_ENTRY_UPSERTED = "PriceListEntryUpserted"
