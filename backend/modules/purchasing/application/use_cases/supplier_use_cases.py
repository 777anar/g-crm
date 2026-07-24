from sqlalchemy.orm import Session

from core.api.errors import NotFoundError
from core.audit.service import record_audit
from core.events.event_bus import event_bus
from core.events.event_envelope import Event
from modules.purchasing.application.dtos import CreateSupplierInput, UpdateSupplierInput
from modules.purchasing.domain import events as purchasing_events
from modules.purchasing.domain.value_objects import VALID_SUPPLIER_STATUSES
from modules.purchasing.infrastructure.models.supplier import Supplier
from modules.purchasing.infrastructure.repositories.supplier_repository import SupplierRepository

MODULE = "purchasing"


class CreateSupplierUseCase:
    def __init__(self, db: Session):
        self.db = db
        self.suppliers = SupplierRepository(db)

    def execute(self, data: CreateSupplierInput) -> Supplier:
        supplier = Supplier(
            company_id=data.company_id,
            name=data.name,
            contact_name=data.contact_name,
            phone=data.phone,
            email=data.email,
            address=data.address,
            notes=data.notes,
            tax_id=data.tax_id,
            payment_terms_days=data.payment_terms_days,
            default_currency=data.default_currency.upper(),
            created_by=data.actor_user_id,
        )
        self.suppliers.add(supplier)

        record_audit(
            self.db,
            company_id=data.company_id,
            module=MODULE,
            actor_user_id=data.actor_user_id,
            action="supplier.created",
            entity_type="supplier",
            entity_id=supplier.id,
            diff={"name": supplier.name},
        )
        self.db.flush()

        event_bus.publish(
            Event(
                name=purchasing_events.SUPPLIER_CREATED,
                company_id=data.company_id,
                payload={"supplier_id": str(supplier.id), "name": supplier.name},
                published_by_module=MODULE,
            ),
            self.db,
        )
        return supplier


class UpdateSupplierUseCase:
    def __init__(self, db: Session):
        self.db = db
        self.suppliers = SupplierRepository(db)

    def execute(self, data: UpdateSupplierInput) -> Supplier:
        supplier = self.suppliers.get(company_id=data.company_id, supplier_id=data.supplier_id)
        if supplier is None:
            raise NotFoundError("Supplier not found")

        if data.name is not None:
            supplier.name = data.name
        if data.contact_name is not None:
            supplier.contact_name = data.contact_name
        if data.phone is not None:
            supplier.phone = data.phone
        if data.email is not None:
            supplier.email = data.email
        if data.address is not None:
            supplier.address = data.address
        if data.notes is not None:
            supplier.notes = data.notes
        if data.status is not None:
            if data.status not in VALID_SUPPLIER_STATUSES:
                raise ValueError(f"status must be one of {sorted(VALID_SUPPLIER_STATUSES)}")
            supplier.status = data.status
        if data.tax_id is not None:
            supplier.tax_id = data.tax_id
        if data.payment_terms_days is not None:
            supplier.payment_terms_days = data.payment_terms_days
        if data.default_currency is not None:
            supplier.default_currency = data.default_currency.upper()

        record_audit(
            self.db,
            company_id=data.company_id,
            module=MODULE,
            actor_user_id=data.actor_user_id,
            action="supplier.updated",
            entity_type="supplier",
            entity_id=supplier.id,
            diff={"name": supplier.name, "status": supplier.status},
        )
        self.db.flush()

        event_bus.publish(
            Event(
                name=purchasing_events.SUPPLIER_UPDATED,
                company_id=data.company_id,
                payload={"supplier_id": str(supplier.id), "name": supplier.name},
                published_by_module=MODULE,
            ),
            self.db,
        )
        return supplier
