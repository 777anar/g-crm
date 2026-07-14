import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from core.api.errors import NotFoundError, ValidationAPIError
from core.audit.service import record_audit
from core.auth.models import UserCompanyRole
from core.events.event_bus import event_bus
from core.events.event_envelope import Event
from modules.crm.application.dtos import (
    AddCustomerNoteInput,
    ArchiveCustomerInput,
    CreateCustomerInput,
    UpdateCustomerInput,
)
from modules.crm.domain import events as crm_events
from modules.crm.domain.value_objects import ACTIVITY_TYPE_NOTE, ACTIVITY_TYPE_SYSTEM, DEFAULT_CUSTOMER_STATUS
from modules.crm.infrastructure.models.activity import Activity
from modules.crm.infrastructure.models.contact import Contact
from modules.crm.infrastructure.models.customer import Customer
from modules.crm.infrastructure.repositories.activity_repository import ActivityRepository
from modules.crm.infrastructure.repositories.contact_repository import ContactRepository
from modules.crm.infrastructure.repositories.customer_repository import CustomerRepository

MODULE_NAME = "crm"


def _ensure_manager_belongs_to_company(db: Session, *, company_id: uuid.UUID, manager_id: uuid.UUID) -> None:
    """Guards against assigning a customer to a UUID that doesn't correspond
    to an actual member of the active company -- a typo'd or malicious
    assigned_manager_id would otherwise be persisted silently."""
    exists = db.scalar(
        select(UserCompanyRole.id).where(
            UserCompanyRole.company_id == company_id, UserCompanyRole.user_id == manager_id
        )
    )
    if exists is None:
        raise ValidationAPIError(
            "assigned_manager_id does not refer to a member of this company",
            details=[{"field": "assigned_manager_id", "issue": "no such user in this company"}],
        )


class CreateCustomerUseCase:
    def __init__(self, db: Session):
        self.db = db
        self.customers = CustomerRepository(db)
        self.contacts = ContactRepository(db)
        self.activities = ActivityRepository(db)

    def execute(self, data: CreateCustomerInput) -> Customer:
        if data.assigned_manager_id is not None:
            _ensure_manager_belongs_to_company(
                self.db, company_id=data.company_id, manager_id=data.assigned_manager_id
            )

        customer = Customer(
            company_id=data.company_id,
            name=data.name,
            type=data.type,
            assigned_manager_id=data.assigned_manager_id,
            lead_source=data.lead_source,
            advertising_campaign=data.advertising_campaign,
            phone=data.phone,
            whatsapp=data.whatsapp,
            instagram=data.instagram,
            facebook=data.facebook,
            email=data.email,
            address=data.address,
            company_name=data.company_name,
            notes=data.notes,
            status=data.status or DEFAULT_CUSTOMER_STATUS,
            tags=data.tags,
            created_by=data.actor_user_id,
        )
        self.customers.add(customer)

        if data.contact_full_name:
            contact = Contact(
                company_id=data.company_id,
                customer_id=customer.id,
                full_name=data.contact_full_name,
                email=data.contact_email,
                phone=data.contact_phone,
                created_by=data.actor_user_id,
            )
            self.contacts.add(contact)
            customer.primary_contact_id = contact.id

        self.activities.add(
            Activity(
                company_id=data.company_id,
                type=ACTIVITY_TYPE_SYSTEM,
                body=f"Customer '{customer.name}' created.",
                related_entity_type="customer",
                related_entity_id=customer.id,
                created_by=data.actor_user_id,
            )
        )

        record_audit(
            self.db,
            company_id=data.company_id,
            module=MODULE_NAME,
            actor_user_id=data.actor_user_id,
            action="customer.created",
            entity_type="customer",
            entity_id=customer.id,
            diff={"name": customer.name, "type": customer.type},
        )
        self.db.flush()

        event_bus.publish(
            Event(
                name=crm_events.CUSTOMER_CREATED,
                company_id=data.company_id,
                payload={"customer_id": str(customer.id), "name": customer.name},
                published_by_module=MODULE_NAME,
            ),
            self.db,
        )
        return customer


class UpdateCustomerUseCase:
    def __init__(self, db: Session):
        self.db = db
        self.customers = CustomerRepository(db)

    def execute(self, data: UpdateCustomerInput) -> Customer:
        customer = self.customers.get_model(company_id=data.company_id, customer_id=data.customer_id)
        if customer is None:
            raise NotFoundError("Customer not found")

        diff = {}
        if data.name is not None and data.name != customer.name:
            diff["name"] = {"old": customer.name, "new": data.name}
            customer.name = data.name
        if data.type is not None and data.type != customer.type:
            diff["type"] = {"old": customer.type, "new": data.type}
            customer.type = data.type
        manager_update_requested = data.clear_assigned_manager or data.assigned_manager_id is not None
        if manager_update_requested and data.assigned_manager_id != customer.assigned_manager_id:
            if data.assigned_manager_id is not None:
                _ensure_manager_belongs_to_company(
                    self.db, company_id=data.company_id, manager_id=data.assigned_manager_id
                )
            diff["assigned_manager_id"] = {
                "old": str(customer.assigned_manager_id) if customer.assigned_manager_id else None,
                "new": str(data.assigned_manager_id) if data.assigned_manager_id else None,
            }
            customer.assigned_manager_id = data.assigned_manager_id
        if data.lead_source is not None and data.lead_source != customer.lead_source:
            diff["lead_source"] = {"old": customer.lead_source, "new": data.lead_source}
            customer.lead_source = data.lead_source
        if data.advertising_campaign is not None and data.advertising_campaign != customer.advertising_campaign:
            diff["advertising_campaign"] = {"old": customer.advertising_campaign, "new": data.advertising_campaign}
            customer.advertising_campaign = data.advertising_campaign
        for field_name in ("phone", "whatsapp", "instagram", "facebook", "email", "address", "company_name", "notes"):
            new_value = getattr(data, field_name)
            if new_value is not None and new_value != getattr(customer, field_name):
                diff[field_name] = {"old": getattr(customer, field_name), "new": new_value}
                setattr(customer, field_name, new_value)
        if data.tags is not None and data.tags != list(customer.tags or []):
            diff["tags"] = {"old": customer.tags, "new": data.tags}
            customer.tags = data.tags

        status_changed = False
        old_status = customer.status
        if data.status is not None and data.status != customer.status:
            diff["status"] = {"old": customer.status, "new": data.status}
            customer.status = data.status
            status_changed = True

        record_audit(
            self.db,
            company_id=data.company_id,
            module=MODULE_NAME,
            actor_user_id=data.actor_user_id,
            action="customer.updated",
            entity_type="customer",
            entity_id=customer.id,
            diff=diff,
        )
        self.db.flush()

        event_bus.publish(
            Event(
                name=crm_events.CUSTOMER_UPDATED,
                company_id=data.company_id,
                payload={"customer_id": str(customer.id), "diff": diff},
                published_by_module=MODULE_NAME,
            ),
            self.db,
        )

        if status_changed:
            event_bus.publish(
                Event(
                    name=crm_events.CUSTOMER_STATUS_CHANGED,
                    company_id=data.company_id,
                    payload={"customer_id": str(customer.id), "old_status": old_status, "new_status": customer.status},
                    published_by_module=MODULE_NAME,
                ),
                self.db,
            )
        return customer


class ArchiveCustomerUseCase:
    def __init__(self, db: Session):
        self.db = db
        self.customers = CustomerRepository(db)

    def execute(self, data: ArchiveCustomerInput) -> Customer:
        customer = self.customers.get_model(company_id=data.company_id, customer_id=data.customer_id)
        if customer is None:
            raise NotFoundError("Customer not found")
        from modules.crm.domain.exceptions import CustomerAlreadyArchivedError

        if customer.deleted_at is not None:
            raise CustomerAlreadyArchivedError(f"Customer {customer.id} is already archived")

        customer.deleted_at = datetime.now(timezone.utc)

        record_audit(
            self.db,
            company_id=data.company_id,
            module=MODULE_NAME,
            actor_user_id=data.actor_user_id,
            action="customer.archived",
            entity_type="customer",
            entity_id=customer.id,
        )
        self.db.flush()

        event_bus.publish(
            Event(
                name=crm_events.CUSTOMER_ARCHIVED,
                company_id=data.company_id,
                payload={"customer_id": str(customer.id)},
                published_by_module=MODULE_NAME,
            ),
            self.db,
        )
        return customer


class AddCustomerNoteUseCase:
    def __init__(self, db: Session):
        self.db = db
        self.customers = CustomerRepository(db)
        self.activities = ActivityRepository(db)

    def execute(self, data: AddCustomerNoteInput) -> Activity:
        customer = self.customers.get_model(company_id=data.company_id, customer_id=data.customer_id)
        if customer is None:
            raise NotFoundError("Customer not found")

        note = Activity(
            company_id=data.company_id,
            type=ACTIVITY_TYPE_NOTE,
            body=data.body,
            related_entity_type="customer",
            related_entity_id=customer.id,
            created_by=data.actor_user_id,
        )
        self.activities.add(note)

        record_audit(
            self.db,
            company_id=data.company_id,
            module=MODULE_NAME,
            actor_user_id=data.actor_user_id,
            action="customer.note_added",
            entity_type="customer",
            entity_id=customer.id,
            diff={"note_id": str(note.id)},
        )
        self.db.flush()

        event_bus.publish(
            Event(
                name=crm_events.CUSTOMER_NOTE_ADDED,
                company_id=data.company_id,
                payload={"customer_id": str(customer.id), "note_id": str(note.id)},
                published_by_module=MODULE_NAME,
            ),
            self.db,
        )
        return note
