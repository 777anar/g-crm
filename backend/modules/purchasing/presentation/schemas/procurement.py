import uuid
from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class ContactCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    job_title: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    is_primary: bool = False


class ContactOut(ContactCreate):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    supplier_id: uuid.UUID
    created_at: datetime


class RFQLineInput(BaseModel):
    material_id: Optional[uuid.UUID] = None
    description: str = Field(min_length=1, max_length=500)
    quantity: Decimal = Field(gt=0)
    unit: str = "unit"
    quoted_unit_cost: Optional[Decimal] = Field(default=None, ge=0)


class RFQCreate(BaseModel):
    supplier_id: uuid.UUID
    currency: str = Field(default="AZN", min_length=3, max_length=3)
    response_due_date: Optional[str] = None
    supplier_reference: Optional[str] = None
    notes: Optional[str] = None
    lines: List[RFQLineInput] = Field(min_length=1)


class RFQUpdate(BaseModel):
    status: str
    quoted_total: Optional[Decimal] = Field(default=None, ge=0)
    supplier_reference: Optional[str] = None


class RFQLineOut(RFQLineInput):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    rfq_id: uuid.UUID
    sort_order: int


class RFQOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    supplier_id: uuid.UUID
    rfq_number: str
    status: str
    currency: str
    response_due_date: Optional[str]
    quoted_total: Optional[Decimal]
    supplier_reference: Optional[str]
    notes: Optional[str]
    created_at: datetime
    updated_at: datetime
    lines: List[RFQLineOut] = []


class ReturnLineInput(BaseModel):
    goods_receipt_id: uuid.UUID
    quantity: Decimal = Field(gt=0)


class ReturnCreate(BaseModel):
    purchase_order_id: uuid.UUID
    reason: str = Field(min_length=3)
    lines: List[ReturnLineInput] = Field(min_length=1)


class ReturnLineOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    goods_receipt_id: uuid.UUID
    quantity: Decimal
    unit_cost: Decimal
    line_total: Decimal


class ReturnOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    supplier_id: uuid.UUID
    purchase_order_id: uuid.UUID
    return_number: str
    status: str
    reason: str
    total_amount: Decimal
    created_at: datetime
    completed_at: Optional[datetime]
    lines: List[ReturnLineOut] = []


class PaymentUpdate(BaseModel):
    amount_paid: Decimal = Field(ge=0)
    payment_due_date: Optional[str] = None


class AttachmentCreate(BaseModel):
    entity_type: str
    entity_id: uuid.UUID
    document_id: uuid.UUID
    label: Optional[str] = None


class AttachmentOut(AttachmentCreate):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    created_at: datetime


class SupplierMetricsOut(BaseModel):
    supplier_id: uuid.UUID
    total_orders: int
    total_spend: Decimal
    open_orders: int
    completed_orders: int
    on_time_delivery_rate: float
    fill_rate: float
    return_rate: float
    outstanding_amount: Decimal


class ProcurementDashboardOut(BaseModel):
    supplier_count: int
    open_rfqs: int
    pending_approvals: int
    open_orders: int
    overdue_orders: int
    outstanding_payables: Decimal
    recent_orders: list[dict]
