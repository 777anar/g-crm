import uuid
from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel

# ── Admin (staff-facing) access management ──────────────────────────────────


class EnablePortalAccessRequest(BaseModel):
    email: str
    password: str


class ResetPortalPasswordRequest(BaseModel):
    password: str


class SetPortalAccessActiveRequest(BaseModel):
    is_active: bool


class PortalAccessOut(BaseModel):
    customer_id: uuid.UUID
    email: str
    is_active: bool
    last_login_at: Optional[datetime]
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Customer-facing auth ─────────────────────────────────────────────────────


class PortalLoginRequest(BaseModel):
    email: str
    password: str


class PortalTokenResponse(BaseModel):
    # Kept in the body for Bearer-token API clients and backward
    # compatibility; the portal frontend now authenticates via the httpOnly
    # cookies set alongside this response instead (Phase 18, mirrors
    # core/auth/schemas.py's TokenResponse).
    access_token: str
    refresh_token: str


class PortalRefreshRequest(BaseModel):
    # Optional: the portal frontend relies on the httpOnly refresh cookie
    # instead of holding this in JS-readable storage (Phase 18).
    refresh_token: Optional[str] = None


class PortalAccessTokenOut(BaseModel):
    access_token: str


# ── Customer-facing profile & data, deliberately whitelisted -- never a bare
# model_validate() of the internal staff-facing schema. Order/Quote both
# carry total_internal_cost/total_profit/profit_margin_pct (COGS and margin)
# that a customer must never see; Quote also has internal_notes; Order has
# production_notes/installation_notes. Every field below is chosen, not
# inherited, for exactly that reason. ────────────────────────────────────────


class PortalMeOut(BaseModel):
    customer_id: uuid.UUID
    name: str
    email: str
    phone: Optional[str]
    company_id: uuid.UUID
    company_name: str


class PortalOrderOut(BaseModel):
    id: uuid.UUID
    order_number: str
    status: str
    currency: str
    subtotal_gross: Decimal
    discount_amount: Decimal
    vat_amount: Decimal
    total_final: Decimal
    delivery_address: Optional[str]
    scheduled_production_date: Optional[str]
    scheduled_installation_date: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


class PortalOrderListOut(BaseModel):
    items: List[PortalOrderOut]
    next_cursor: Optional[str] = None


class PortalQuoteOut(BaseModel):
    id: uuid.UUID
    quote_number: str
    version: int
    status: str
    currency: str
    subtotal_gross: Decimal
    discount_amount: Decimal
    vat_amount: Decimal
    total_final: Decimal
    valid_until: Optional[str]
    customer_notes: Optional[str]
    sent_at: Optional[datetime]
    accepted_at: Optional[datetime]
    rejected_at: Optional[datetime]
    created_at: datetime

    model_config = {"from_attributes": True}


class PortalQuoteListOut(BaseModel):
    items: List[PortalQuoteOut]
    next_cursor: Optional[str] = None


class PortalInvoiceOut(BaseModel):
    id: uuid.UUID
    invoice_number: str
    status: str
    currency: str
    subtotal_amount: Decimal
    total_amount: Decimal
    amount_paid: Decimal
    balance_due: Decimal
    issue_date: str
    due_date: Optional[str]
    notes: Optional[str]
    sent_at: Optional[datetime]
    paid_at: Optional[datetime]
    created_at: datetime

    model_config = {"from_attributes": True}


class PortalInvoiceListOut(BaseModel):
    items: List[PortalInvoiceOut]
    next_cursor: Optional[str] = None


class PortalInstallationJobOut(BaseModel):
    id: uuid.UUID
    job_number: str
    status: str
    scheduled_date: Optional[str]
    scheduled_time_slot: Optional[str]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    created_at: datetime

    model_config = {"from_attributes": True}


class PortalInstallationJobListOut(BaseModel):
    items: List[PortalInstallationJobOut]
    next_cursor: Optional[str] = None


class PortalDocumentOut(BaseModel):
    id: uuid.UUID
    related_entity_type: str
    mime_type: str
    created_at: datetime

    model_config = {"from_attributes": True}


class PortalDocumentListOut(BaseModel):
    items: List[PortalDocumentOut]
    next_cursor: Optional[str] = None


class PortalSignedUrlOut(BaseModel):
    url: str
