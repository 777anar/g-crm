"""Domain events published by the Sales module."""

PROJECT_CREATED = "ProjectCreated"
PROJECT_UPDATED = "ProjectUpdated"

QUOTE_CREATED = "QuoteCreated"
QUOTE_VERSION_CREATED = "QuoteVersionCreated"
QUOTE_STATUS_CHANGED = "QuoteStatusChanged"
QUOTE_ACCEPTED = "QuoteAccepted"
QUOTE_REJECTED = "QuoteRejected"
QUOTE_EXPIRED = "QuoteExpired"

SLAB_RESERVED = "SlabReserved"
SLAB_RELEASED = "SlabReleased"

# Sprint 3: Project workspace (Rooms / Project Items / Measurements / Drawings / Photos)
ROOM_CREATED = "RoomCreated"
ROOM_UPDATED = "RoomUpdated"
ROOM_DELETED = "RoomDeleted"

PROJECT_ITEM_CREATED = "ProjectItemCreated"
PROJECT_ITEM_UPDATED = "ProjectItemUpdated"
PROJECT_ITEM_DELETED = "ProjectItemDeleted"

PROJECT_ITEM_MEASUREMENT_RECORDED = "ProjectItemMeasurementRecorded"
PROJECT_ITEM_MEASUREMENT_UPDATED = "ProjectItemMeasurementUpdated"
PROJECT_ITEM_MEASUREMENT_DELETED = "ProjectItemMeasurementDeleted"

PROJECT_ITEM_DRAWING_ADDED = "ProjectItemDrawingAdded"
PROJECT_ITEM_DRAWING_DELETED = "ProjectItemDrawingDeleted"

PROJECT_ITEM_PHOTO_ADDED = "ProjectItemPhotoAdded"
PROJECT_ITEM_PHOTO_DELETED = "ProjectItemPhotoDeleted"
