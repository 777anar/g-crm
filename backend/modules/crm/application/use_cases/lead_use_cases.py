from datetime import datetime, timezone

from sqlalchemy.orm import Session

from core.api.errors import NotFoundError, ValidationAPIError
from core.audit.service import record_audit
from core.events.event_bus import event_bus
from core.events.event_envelope import Event
from modules.crm.application.dtos import ConvertLeadInput, CreateLeadInput
from modules.crm.domain import events as crm_events
from modules.crm.domain.exceptions import LeadAlreadyConvertedError
from modules.crm.domain.value_objects import (
    ACTIVITY_TYPE_SYSTEM,
    CUSTOMER_TYPE_INDIVIDUAL,
    LEAD_STATUS_CONVERTED,
    VALID_LEAD_SOURCES,
)
from modules.crm.infrastructure.models.activity import Activity
from modules.crm.infrastructure.models.contact import Contact
from modules.crm.infrastructure.models.customer import Customer
from modules.crm.infrastructure.models.lead import Lead
from modules.crm.infrastructure.repositories.activity_repository import ActivityRepository
from modules.crm.infrastructure.repositories.contact_repository import ContactRepository
from modules.crm.infrastructure.repositories.customer_repository import CustomerRepository
from modules.crm.infrastructure.repositories.lead_repository import LeadRepository

MODULE_NAME = "crm"


class CreateLeadUseCase:
    """Single entry point for all lead-capture channels (Instagram, Facebook,
    Messenger, WhatsApp, Manual) -- the channel is a field, not a separate
    code path, so adding a future automated channel integration (e.g. a
    WhatsApp webhook) means calling this same use-case with
    source_channel='whatsapp', not building a parallel pipeline."""

    def __init__(self, db: Session):
        self.db = db
        self.leads = LeadRepository(db)

    def execute(self, data: CreateLeadInput) -> Lead:
        if data.source_channel not in VALID_LEAD_SOURCES:
            raise ValidationAPIError(
                f"Invalid lead source channel '{data.source_channel}'",
                details=[{"field": "source_channel", "issue": f"must be one of {sorted(VALID_LEAD_SOURCES)}"}],
            )

        lead = Lead(
            company_id=data.company_id,
            full_name=data.full_name,
            email=data.email,
            phone=data.phone,
            source_channel=data.source_channel,
            campaign=data.campaign,
            campaign_id=data.campaign_id,
            assigned_manager_id=data.assigned_manager_id,
            created_by=data.actor_user_id,
        )
        self.leads.add(lead)

        record_audit(
            self.db,
            company_id=data.company_id,
            module=MODULE_NAME,
            actor_user_id=data.actor_user_id,
            action="lead.created",
            entity_type="lead",
            entity_id=lead.id,
            diff={"source_channel": lead.source_channel},
        )
        self.db.flush()

        event_bus.publish(
            Event(
                name=crm_events.LEAD_CREATED,
                company_id=data.company_id,
                payload={
                    "lead_id": str(lead.id),
                    "source_channel": lead.source_channel,
                    "full_name": lead.full_name,
                },
                published_by_module=MODULE_NAME,
            ),
            self.db,
        )
        return lead


class ConvertLeadUseCase:
    """Converts a Lead into a Customer (+ primary Contact), per the
    CRM functional requirements' lead-to-customer pipeline."""

    def __init__(self, db: Session):
        self.db = db
        self.leads = LeadRepository(db)
        self.customers = CustomerRepository(db)
        self.contacts = ContactRepository(db)
        self.activities = ActivityRepository(db)

    def execute(self, data: ConvertLeadInput) -> Customer:
        lead = self.leads.get(company_id=data.company_id, lead_id=data.lead_id)
        if lead is None:
            raise NotFoundError("Lead not found")
        if lead.status == LEAD_STATUS_CONVERTED:
            raise LeadAlreadyConvertedError(f"Lead {lead.id} has already been converted")

        contact = Contact(
            company_id=data.company_id,
            full_name=lead.full_name,
            email=lead.email,
            phone=lead.phone,
            source=lead.source_channel,
            created_by=data.actor_user_id,
        )
        self.contacts.add(contact)

        customer = Customer(
            company_id=data.company_id,
            name=lead.full_name,
            type=CUSTOMER_TYPE_INDIVIDUAL,
            primary_contact_id=contact.id,
            assigned_manager_id=lead.assigned_manager_id,
            lead_source=lead.source_channel,
            advertising_campaign=lead.campaign,
            created_by=data.actor_user_id,
        )
        self.customers.add(customer)
        contact.customer_id = customer.id

        now = datetime.now(timezone.utc)
        lead.status = LEAD_STATUS_CONVERTED
        lead.converted_customer_id = customer.id
        lead.converted_contact_id = contact.id
        lead.converted_at = now

        self.activities.add(
            Activity(
                company_id=data.company_id,
                type=ACTIVITY_TYPE_SYSTEM,
                body=f"Converted from lead (source: {lead.source_channel}).",
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
            action="lead.converted",
            entity_type="lead",
            entity_id=lead.id,
            diff={"customer_id": str(customer.id)},
        )
        self.db.flush()

        event_bus.publish(
            Event(
                name=crm_events.LEAD_CONVERTED,
                company_id=data.company_id,
                payload={"lead_id": str(lead.id), "customer_id": str(customer.id), "contact_id": str(contact.id)},
                published_by_module=MODULE_NAME,
            ),
            self.db,
        )
        return customer
