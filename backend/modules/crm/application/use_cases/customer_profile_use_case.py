import uuid
from dataclasses import dataclass, field
from typing import List, Optional

from sqlalchemy.orm import Session

from core.api.errors import NotFoundError
from core.storage.models import Document
from modules.crm.infrastructure.models.activity import Activity
from modules.crm.infrastructure.models.contact import Contact
from modules.crm.infrastructure.models.customer import Customer
from modules.crm.infrastructure.repositories.activity_repository import ActivityRepository
from modules.crm.infrastructure.repositories.contact_repository import ContactRepository
from modules.crm.infrastructure.repositories.customer_repository import CustomerRepository


@dataclass
class CustomerProfile:
    customer: Customer
    contacts: List[Contact]
    attachments: List[Document]
    timeline: List[Activity]
    # Projects/Quotes/Orders/Payments are owned by the Production, Sales, and
    # Finance modules respectively -- none are installed yet (Phase 1/2 of
    # the roadmap only builds Foundation + CRM + Sales-to-come). These keys
    # are real, intentionally empty sections, not placeholders: once those
    # modules exist, this use-case calls their public read APIs (never their
    # internals, per the plugin architecture) to populate them.
    projects: List[dict] = field(default_factory=list)
    quotes: List[dict] = field(default_factory=list)
    orders: List[dict] = field(default_factory=list)
    payments: List[dict] = field(default_factory=list)


class GetCustomerProfileUseCase:
    def __init__(self, db: Session):
        self.db = db
        self.customers = CustomerRepository(db)
        self.contacts = ContactRepository(db)
        self.activities = ActivityRepository(db)

    def execute(self, *, company_id: uuid.UUID, customer_id: uuid.UUID) -> CustomerProfile:
        customer = self.customers.get_model(company_id=company_id, customer_id=customer_id)
        if customer is None:
            raise NotFoundError("Customer not found")

        contacts = self.contacts.list_for_customer(company_id=company_id, customer_id=customer_id)

        attachments = list(
            self.db.query(Document)
            .filter(
                Document.company_id == company_id,
                Document.related_entity_type == "customer",
                Document.related_entity_id == customer_id,
            )
            .order_by(Document.created_at.desc())
            .all()
        )

        timeline = self.activities.list_for_entity(
            company_id=company_id, related_entity_type="customer", related_entity_id=customer_id
        )

        return CustomerProfile(customer=customer, contacts=contacts, attachments=attachments, timeline=timeline)
