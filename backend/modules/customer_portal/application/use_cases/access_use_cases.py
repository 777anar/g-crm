from sqlalchemy import select
from sqlalchemy.orm import Session

from core.api.errors import ConflictError, NotFoundError
from core.audit.service import record_audit
from core.auth.security import hash_password
from core.events.event_bus import event_bus
from core.events.event_envelope import Event
from modules.crm.infrastructure.models.customer import Customer
from modules.customer_portal.application.dtos import (
    EnablePortalAccessInput,
    ResetPortalPasswordInput,
    SetPortalAccessActiveInput,
)
from modules.customer_portal.domain import events as portal_events
from modules.customer_portal.infrastructure.models.customer_login import CustomerLogin
from modules.customer_portal.infrastructure.repositories.customer_login_repository import CustomerLoginRepository

MODULE = "customer_portal"


def _get_customer_or_404(db: Session, *, company_id, customer_id) -> Customer:
    customer = db.scalar(select(Customer).where(Customer.id == customer_id, Customer.company_id == company_id))
    if customer is None:
        raise NotFoundError("Customer not found")
    return customer


class EnablePortalAccessUseCase:
    def __init__(self, db: Session):
        self.db = db
        self.logins = CustomerLoginRepository(db)

    def execute(self, data: EnablePortalAccessInput) -> CustomerLogin:
        _get_customer_or_404(self.db, company_id=data.company_id, customer_id=data.customer_id)

        if self.logins.get_by_customer(company_id=data.company_id, customer_id=data.customer_id) is not None:
            raise ConflictError("Portal access is already enabled for this customer")
        if self.logins.get_by_email(email=data.email) is not None:
            raise ConflictError("This email is already used by another portal login")

        login = CustomerLogin(
            company_id=data.company_id,
            customer_id=data.customer_id,
            email=data.email,
            password_hash=hash_password(data.password),
            is_active=True,
        )
        self.logins.add(login)

        record_audit(
            self.db,
            company_id=data.company_id,
            module=MODULE,
            actor_user_id=data.actor_user_id,
            action="portal_access.enabled",
            entity_type="customer_portal_login",
            entity_id=login.id,
            diff={"customer_id": str(data.customer_id), "email": login.email},
        )
        self.db.flush()

        event_bus.publish(
            Event(
                name=portal_events.PORTAL_ACCESS_ENABLED,
                company_id=data.company_id,
                payload={"customer_id": str(data.customer_id), "customer_login_id": str(login.id)},
                published_by_module=MODULE,
            ),
            self.db,
        )
        return login


class ResetPortalPasswordUseCase:
    def __init__(self, db: Session):
        self.db = db
        self.logins = CustomerLoginRepository(db)

    def execute(self, data: ResetPortalPasswordInput) -> CustomerLogin:
        login = self.logins.get_by_customer(company_id=data.company_id, customer_id=data.customer_id)
        if login is None:
            raise NotFoundError("Portal access is not enabled for this customer")

        login.password_hash = hash_password(data.password)

        record_audit(
            self.db,
            company_id=data.company_id,
            module=MODULE,
            actor_user_id=data.actor_user_id,
            action="portal_access.password_reset",
            entity_type="customer_portal_login",
            entity_id=login.id,
            diff={"customer_id": str(data.customer_id)},
        )
        self.db.flush()

        event_bus.publish(
            Event(
                name=portal_events.PORTAL_ACCESS_PASSWORD_RESET,
                company_id=data.company_id,
                payload={"customer_id": str(data.customer_id), "customer_login_id": str(login.id)},
                published_by_module=MODULE,
            ),
            self.db,
        )
        return login


class SetPortalAccessActiveUseCase:
    def __init__(self, db: Session):
        self.db = db
        self.logins = CustomerLoginRepository(db)

    def execute(self, data: SetPortalAccessActiveInput) -> CustomerLogin:
        login = self.logins.get_by_customer(company_id=data.company_id, customer_id=data.customer_id)
        if login is None:
            raise NotFoundError("Portal access is not enabled for this customer")

        old_active = login.is_active
        login.is_active = data.is_active

        record_audit(
            self.db,
            company_id=data.company_id,
            module=MODULE,
            actor_user_id=data.actor_user_id,
            action="portal_access.status_changed",
            entity_type="customer_portal_login",
            entity_id=login.id,
            diff={"is_active": {"old": old_active, "new": login.is_active}},
        )
        self.db.flush()

        event_bus.publish(
            Event(
                name=portal_events.PORTAL_ACCESS_STATUS_CHANGED,
                company_id=data.company_id,
                payload={"customer_id": str(data.customer_id), "is_active": login.is_active},
                published_by_module=MODULE,
            ),
            self.db,
        )
        return login
