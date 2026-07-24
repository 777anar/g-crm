import csv
import io
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from core.api.errors import BusinessRuleViolationError, ForbiddenError, NotFoundError
from core.audit.service import record_audit
from core.auth.models import ROLE_MANAGER, ROLE_OWNER
from core.db.session import get_db
from core.events.event_bus import event_bus
from core.events.event_envelope import Event
from core.rbac.dependencies import CurrentUser, require_permission
from core.storage.models import Document
from modules.catalog.infrastructure.models.slab import Slab
from modules.purchasing.application.dtos import CreatePurchaseOrderInput, PurchaseOrderLineInput
from modules.purchasing.application.use_cases import CreatePurchaseOrderUseCase
from modules.purchasing.domain import events
from modules.purchasing.domain.value_objects import PAYMENT_STATUSES, RETURN_STATUSES, RFQ_STATUSES
from modules.purchasing.infrastructure.models import (
    GoodsReceipt, PurchaseAttachment, PurchaseOrder, PurchaseOrderLine, PurchaseReturn,
    PurchaseReturnLine, PurchaseRFQ, PurchaseRFQLine, Supplier, SupplierContact,
)
from modules.purchasing.presentation.schemas.procurement import (
    AttachmentCreate, AttachmentOut, ContactCreate, ContactOut, PaymentUpdate,
    ProcurementDashboardOut, ReturnCreate, ReturnLineOut, ReturnOut, RFQCreate,
    RFQLineOut, RFQOut, RFQUpdate, SupplierMetricsOut,
)
from modules.purchasing.presentation.schemas.purchase_order import PurchaseOrderOut

router = APIRouter()


def _get(db, model, company_id, object_id, message):
    obj = db.scalar(select(model).where(model.id == object_id, model.company_id == company_id))
    if obj is None:
        raise NotFoundError(message)
    return obj


def _write(db, user, action, entity_type, entity_id, event_name, payload):
    record_audit(db, company_id=user.active_company_id, module="purchasing", actor_user_id=user.user_id,
                 action=action, entity_type=entity_type, entity_id=entity_id, diff=payload)
    event_bus.publish(Event(name=event_name, company_id=user.active_company_id, payload=payload,
                            published_by_module="purchasing"), db)


@router.get("/suppliers/{supplier_id}/contacts", response_model=list[ContactOut])
def contacts(supplier_id: uuid.UUID, db: Session = Depends(get_db),
             user: CurrentUser = Depends(require_permission("purchasing:suppliers:read"))):
    _get(db, Supplier, user.active_company_id, supplier_id, "Supplier not found")
    return list(db.scalars(select(SupplierContact).where(SupplierContact.company_id == user.active_company_id,
        SupplierContact.supplier_id == supplier_id).order_by(SupplierContact.is_primary.desc(), SupplierContact.name)).all())


@router.post("/suppliers/{supplier_id}/contacts", response_model=ContactOut)
def add_contact(supplier_id: uuid.UUID, body: ContactCreate, db: Session = Depends(get_db),
                user: CurrentUser = Depends(require_permission("purchasing:suppliers:write"))):
    _get(db, Supplier, user.active_company_id, supplier_id, "Supplier not found")
    if body.is_primary:
        for row in db.scalars(select(SupplierContact).where(SupplierContact.company_id == user.active_company_id,
                SupplierContact.supplier_id == supplier_id)).all(): row.is_primary = False
    contact = SupplierContact(company_id=user.active_company_id, supplier_id=supplier_id, **body.model_dump())
    db.add(contact); db.flush()
    _write(db, user, "supplier.contact_created", "supplier_contact", contact.id, events.SUPPLIER_CONTACT_CREATED,
           {"supplier_id": str(supplier_id), "contact_id": str(contact.id)})
    db.commit(); db.refresh(contact); return contact


@router.delete("/suppliers/{supplier_id}/contacts/{contact_id}", status_code=204)
def delete_contact(supplier_id: uuid.UUID, contact_id: uuid.UUID, db: Session = Depends(get_db),
                   user: CurrentUser = Depends(require_permission("purchasing:suppliers:write"))):
    contact = _get(db, SupplierContact, user.active_company_id, contact_id, "Supplier contact not found")
    if contact.supplier_id != supplier_id: raise NotFoundError("Supplier contact not found")
    record_audit(db, company_id=user.active_company_id, module="purchasing", actor_user_id=user.user_id,
                 action="supplier.contact_deleted", entity_type="supplier_contact", entity_id=contact.id,
                 diff={"supplier_id": str(supplier_id), "name": contact.name})
    db.delete(contact); db.commit()


def _rfq_out(db, rfq):
    out = RFQOut.model_validate(rfq)
    out.lines = [RFQLineOut.model_validate(x) for x in db.scalars(select(PurchaseRFQLine).where(
        PurchaseRFQLine.company_id == rfq.company_id, PurchaseRFQLine.rfq_id == rfq.id).order_by(PurchaseRFQLine.sort_order)).all()]
    return out


@router.get("/rfqs", response_model=list[RFQOut])
def list_rfqs(status: str | None = None, supplier_id: uuid.UUID | None = None, search: str | None = None,
              db: Session = Depends(get_db), user: CurrentUser = Depends(require_permission("purchasing:rfqs:read"))):
    stmt = select(PurchaseRFQ).where(PurchaseRFQ.company_id == user.active_company_id)
    if status: stmt = stmt.where(PurchaseRFQ.status == status)
    if supplier_id: stmt = stmt.where(PurchaseRFQ.supplier_id == supplier_id)
    if search: stmt = stmt.where(PurchaseRFQ.rfq_number.ilike(f"%{search.strip()}%"))
    return [_rfq_out(db, x) for x in db.scalars(stmt.order_by(PurchaseRFQ.created_at.desc()).limit(200)).all()]


@router.post("/rfqs", response_model=RFQOut)
def create_rfq(body: RFQCreate, db: Session = Depends(get_db),
               user: CurrentUser = Depends(require_permission("purchasing:rfqs:write"))):
    supplier = _get(db, Supplier, user.active_company_id, body.supplier_id, "Supplier not found")
    if supplier.status != "active": raise BusinessRuleViolationError("Inactive supplier cannot receive an RFQ")
    count = db.scalar(select(func.count(PurchaseRFQ.id)).where(PurchaseRFQ.company_id == user.active_company_id)) or 0
    rfq = PurchaseRFQ(company_id=user.active_company_id, supplier_id=body.supplier_id,
        rfq_number=f"RFQ-{datetime.now().year}-{count + 1:04d}", currency=body.currency.upper(),
        response_due_date=body.response_due_date, supplier_reference=body.supplier_reference,
        notes=body.notes, created_by=user.user_id)
    db.add(rfq); db.flush()
    for i, line in enumerate(body.lines): db.add(PurchaseRFQLine(company_id=user.active_company_id,
        rfq_id=rfq.id, sort_order=i, **line.model_dump()))
    _write(db, user, "rfq.created", "purchase_rfq", rfq.id, events.RFQ_CREATED,
           {"rfq_id": str(rfq.id), "rfq_number": rfq.rfq_number, "supplier_id": str(body.supplier_id)})
    db.commit(); db.refresh(rfq); return _rfq_out(db, rfq)


@router.get("/rfqs/{rfq_id}", response_model=RFQOut)
def get_rfq(rfq_id: uuid.UUID, db: Session = Depends(get_db),
            user: CurrentUser = Depends(require_permission("purchasing:rfqs:read"))):
    return _rfq_out(db, _get(db, PurchaseRFQ, user.active_company_id, rfq_id, "RFQ not found"))


@router.post("/rfqs/{rfq_id}/status", response_model=RFQOut)
def update_rfq(rfq_id: uuid.UUID, body: RFQUpdate, db: Session = Depends(get_db),
               user: CurrentUser = Depends(require_permission("purchasing:rfqs:write"))):
    if body.status not in RFQ_STATUSES: raise BusinessRuleViolationError("Invalid RFQ status")
    rfq = _get(db, PurchaseRFQ, user.active_company_id, rfq_id, "RFQ not found")
    transitions={"draft":{"sent","cancelled"},"sent":{"quoted","cancelled"},"quoted":{"accepted","rejected","cancelled"},
                 "accepted":set(),"rejected":set(),"cancelled":set()}
    if body.status != rfq.status and body.status not in transitions.get(rfq.status,set()):
        raise BusinessRuleViolationError(f"Cannot move RFQ from '{rfq.status}' to '{body.status}'")
    old = rfq.status; rfq.status = body.status
    if body.quoted_total is not None: rfq.quoted_total = body.quoted_total
    if body.supplier_reference is not None: rfq.supplier_reference = body.supplier_reference
    _write(db, user, "rfq.status_changed", "purchase_rfq", rfq.id, events.RFQ_STATUS_CHANGED,
           {"rfq_id": str(rfq.id), "old_status": old, "new_status": body.status})
    db.commit(); db.refresh(rfq); return _rfq_out(db, rfq)


@router.post("/rfqs/{rfq_id}/convert", response_model=PurchaseOrderOut)
def convert_rfq(rfq_id: uuid.UUID, db: Session = Depends(get_db),
                user: CurrentUser = Depends(require_permission("purchasing:purchase_orders:write"))):
    rfq = _get(db, PurchaseRFQ, user.active_company_id, rfq_id, "RFQ not found")
    if rfq.status != "quoted": raise BusinessRuleViolationError("Only a quoted RFQ can be converted")
    lines = list(db.scalars(select(PurchaseRFQLine).where(PurchaseRFQLine.company_id == user.active_company_id,
        PurchaseRFQLine.rfq_id == rfq.id).order_by(PurchaseRFQLine.sort_order)).all())
    if any(x.quoted_unit_cost is None for x in lines): raise BusinessRuleViolationError("Every RFQ line needs a quoted unit cost")
    po = CreatePurchaseOrderUseCase(db).execute(CreatePurchaseOrderInput(company_id=user.active_company_id,
        actor_user_id=user.user_id, supplier_id=rfq.supplier_id, currency=rfq.currency, notes=rfq.notes,
        lines=[PurchaseOrderLineInput(material_id=x.material_id, description=x.description, quantity=x.quantity,
              unit=x.unit, unit_cost=x.quoted_unit_cost) for x in lines]))
    po.rfq_id = rfq.id; rfq.status = "accepted"; db.commit(); db.refresh(po); return po


@router.post("/purchase-orders/{po_id}/payment", response_model=PurchaseOrderOut)
def update_payment(po_id: uuid.UUID, body: PaymentUpdate, db: Session = Depends(get_db),
                   user: CurrentUser = Depends(require_permission("purchasing:payments:write"))):
    po = _get(db, PurchaseOrder, user.active_company_id, po_id, "Purchase order not found")
    if body.amount_paid > po.total_amount: raise BusinessRuleViolationError("Paid amount cannot exceed order total")
    old = po.payment_status; po.amount_paid = body.amount_paid; po.payment_due_date = body.payment_due_date
    po.payment_status = "paid" if body.amount_paid == po.total_amount else ("partially_paid" if body.amount_paid > 0 else "unpaid")
    _write(db, user, "purchase_order.payment_updated", "purchase_order", po.id, events.SUPPLIER_PAYMENT_STATUS_CHANGED,
           {"purchase_order_id": str(po.id), "old_status": old, "new_status": po.payment_status,
            "amount_paid": str(body.amount_paid)})
    db.commit(); db.refresh(po); return po


@router.get("/returns", response_model=list[ReturnOut])
def list_returns(db: Session = Depends(get_db), user: CurrentUser = Depends(require_permission("purchasing:returns:read"))):
    rows = db.scalars(select(PurchaseReturn).where(PurchaseReturn.company_id == user.active_company_id)
                      .order_by(PurchaseReturn.created_at.desc())).all()
    result=[]
    for row in rows:
        out=ReturnOut.model_validate(row); out.lines=[ReturnLineOut.model_validate(x) for x in db.scalars(select(PurchaseReturnLine).where(PurchaseReturnLine.purchase_return_id==row.id)).all()]; result.append(out)
    return result


@router.post("/returns", response_model=ReturnOut)
def create_return(body: ReturnCreate, db: Session = Depends(get_db),
                  user: CurrentUser = Depends(require_permission("purchasing:returns:write"))):
    po = _get(db, PurchaseOrder, user.active_company_id, body.purchase_order_id, "Purchase order not found")
    count = db.scalar(select(func.count(PurchaseReturn.id)).where(PurchaseReturn.company_id == user.active_company_id)) or 0
    ret = PurchaseReturn(company_id=user.active_company_id, supplier_id=po.supplier_id, purchase_order_id=po.id,
        return_number=f"PR-{datetime.now().year}-{count + 1:04d}", reason=body.reason, created_by=user.user_id)
    db.add(ret); db.flush(); total=Decimal("0")
    for item in body.lines:
        receipt = _get(db, GoodsReceipt, user.active_company_id, item.goods_receipt_id, "Goods receipt not found")
        if receipt.purchase_order_id != po.id: raise BusinessRuleViolationError("Receipt does not belong to this order")
        available = Decimal(receipt.quantity_received) - Decimal(receipt.quantity_returned)
        if item.quantity > available: raise BusinessRuleViolationError("Return quantity exceeds received quantity")
        line = _get(db, PurchaseOrderLine, user.active_company_id, receipt.purchase_order_line_id, "Order line not found")
        line_total=item.quantity * Decimal(line.unit_cost); total += line_total
        db.add(PurchaseReturnLine(company_id=user.active_company_id, purchase_return_id=ret.id,
            goods_receipt_id=receipt.id, quantity=item.quantity, unit_cost=line.unit_cost, line_total=line_total))
    ret.total_amount=total
    _write(db, user, "purchase_return.created", "purchase_return", ret.id, events.PURCHASE_RETURN_CREATED,
           {"return_id": str(ret.id), "purchase_order_id": str(po.id), "total_amount": str(total)})
    db.commit(); db.refresh(ret); out=ReturnOut.model_validate(ret)
    out.lines=[ReturnLineOut.model_validate(x) for x in db.scalars(select(PurchaseReturnLine).where(PurchaseReturnLine.purchase_return_id==ret.id)).all()]; return out


@router.post("/returns/{return_id}/complete", response_model=ReturnOut)
def complete_return(return_id: uuid.UUID, db: Session = Depends(get_db),
                    user: CurrentUser = Depends(require_permission("purchasing:returns:write"))):
    ret = _get(db, PurchaseReturn, user.active_company_id, return_id, "Purchase return not found")
    if ret.status != "draft": raise BusinessRuleViolationError("Only a draft return can be completed")
    lines=list(db.scalars(select(PurchaseReturnLine).where(PurchaseReturnLine.company_id==user.active_company_id,
        PurchaseReturnLine.purchase_return_id==ret.id)).all())
    for line in lines:
        receipt=_get(db, GoodsReceipt, user.active_company_id, line.goods_receipt_id, "Goods receipt not found")
        receipt.quantity_returned=Decimal(receipt.quantity_returned)+Decimal(line.quantity)
        if receipt.slab_id:
            slab=db.scalar(select(Slab).where(Slab.id==receipt.slab_id, Slab.company_id==user.active_company_id))
            if slab: slab.status="scrap"
    ret.status="completed"; ret.completed_by=user.user_id; ret.completed_at=datetime.now(timezone.utc)
    _write(db, user, "purchase_return.completed", "purchase_return", ret.id, events.PURCHASE_RETURN_COMPLETED,
           {"return_id": str(ret.id), "total_amount": str(ret.total_amount)})
    db.commit(); db.refresh(ret); out=ReturnOut.model_validate(ret); out.lines=[ReturnLineOut.model_validate(x) for x in lines]; return out


@router.post("/attachments", response_model=AttachmentOut)
def attach(body: AttachmentCreate, db: Session = Depends(get_db),
           user: CurrentUser = Depends(require_permission("purchasing:purchase_orders:write"))):
    if body.entity_type not in {"supplier", "rfq", "purchase_order", "goods_receipt", "purchase_return"}:
        raise BusinessRuleViolationError("Unsupported attachment entity type")
    entity_models={"supplier":Supplier,"rfq":PurchaseRFQ,"purchase_order":PurchaseOrder,
                   "goods_receipt":GoodsReceipt,"purchase_return":PurchaseReturn}
    _get(db, entity_models[body.entity_type], user.active_company_id, body.entity_id, "Attachment target not found")
    doc = db.scalar(select(Document).where(Document.id == body.document_id, Document.company_id == user.active_company_id))
    if doc is None: raise NotFoundError("Document not found")
    row=PurchaseAttachment(company_id=user.active_company_id, added_by=user.user_id, **body.model_dump())
    db.add(row); db.flush(); record_audit(db, company_id=user.active_company_id, module="purchasing",
        actor_user_id=user.user_id, action="attachment.added", entity_type=body.entity_type,
        entity_id=body.entity_id, diff={"document_id": str(body.document_id)})
    db.commit(); db.refresh(row); return row


@router.get("/attachments", response_model=list[AttachmentOut])
def attachments(entity_type: str, entity_id: uuid.UUID, db: Session = Depends(get_db),
                user: CurrentUser = Depends(require_permission("purchasing:purchase_orders:read"))):
    return list(db.scalars(select(PurchaseAttachment).where(PurchaseAttachment.company_id==user.active_company_id,
        PurchaseAttachment.entity_type==entity_type, PurchaseAttachment.entity_id==entity_id)
        .order_by(PurchaseAttachment.created_at.desc())).all())


@router.get("/suppliers/{supplier_id}/metrics", response_model=SupplierMetricsOut)
def supplier_metrics(supplier_id: uuid.UUID, db: Session = Depends(get_db),
                     user: CurrentUser = Depends(require_permission("purchasing:reports:read"))):
    _get(db, Supplier, user.active_company_id, supplier_id, "Supplier not found")
    orders=list(db.scalars(select(PurchaseOrder).where(PurchaseOrder.company_id==user.active_company_id,
        PurchaseOrder.supplier_id==supplier_id)).all())
    receipts=list(db.scalars(select(GoodsReceipt).join(PurchaseOrder, GoodsReceipt.purchase_order_id==PurchaseOrder.id).where(
        GoodsReceipt.company_id==user.active_company_id, PurchaseOrder.supplier_id==supplier_id)).all())
    ordered=sum((Decimal(x.quantity) for po in orders for x in db.scalars(select(PurchaseOrderLine).where(PurchaseOrderLine.purchase_order_id==po.id)).all()),Decimal("0"))
    received=sum((Decimal(x.quantity_received) for x in receipts),Decimal("0")); returned=sum((Decimal(x.quantity_returned) for x in receipts),Decimal("0"))
    completed=[x for x in orders if x.status=="received"]
    on_time=sum(1 for x in completed if not x.expected_delivery_date or x.updated_at.date() <= date.fromisoformat(x.expected_delivery_date))
    return SupplierMetricsOut(supplier_id=supplier_id,total_orders=len(orders),total_spend=sum((Decimal(x.total_amount) for x in orders),Decimal("0")),
        open_orders=sum(x.status not in {"received","cancelled"} for x in orders),completed_orders=len(completed),
        on_time_delivery_rate=round(on_time/len(completed)*100,2) if completed else 0,
        fill_rate=round(float(received/ordered*100),2) if ordered else 0,
        return_rate=round(float(returned/received*100),2) if received else 0,
        outstanding_amount=sum((Decimal(x.total_amount)-Decimal(x.amount_paid) for x in orders),Decimal("0")))


@router.get("/dashboard", response_model=ProcurementDashboardOut)
def dashboard(db: Session = Depends(get_db), user: CurrentUser = Depends(require_permission("purchasing:reports:read"))):
    orders=list(db.scalars(select(PurchaseOrder).where(PurchaseOrder.company_id==user.active_company_id).order_by(PurchaseOrder.created_at.desc())).all())
    today=date.today()
    return ProcurementDashboardOut(supplier_count=db.scalar(select(func.count(Supplier.id)).where(Supplier.company_id==user.active_company_id,Supplier.status=="active")) or 0,
      open_rfqs=db.scalar(select(func.count(PurchaseRFQ.id)).where(PurchaseRFQ.company_id==user.active_company_id,PurchaseRFQ.status.in_(["draft","sent","quoted"]))) or 0,
      pending_approvals=sum(x.status=="pending_approval" for x in orders),open_orders=sum(x.status not in {"received","cancelled"} for x in orders),
      overdue_orders=sum(bool(x.expected_delivery_date and date.fromisoformat(x.expected_delivery_date)<today and x.status not in {"received","cancelled"}) for x in orders),
      outstanding_payables=sum((Decimal(x.total_amount)-Decimal(x.amount_paid) for x in orders if x.status!="cancelled"),Decimal("0")),
      recent_orders=[{"id":str(x.id),"po_number":x.po_number,"status":x.status,"total_amount":str(x.total_amount),"currency":x.currency} for x in orders[:5]])


@router.get("/export/{resource}")
def export(resource: str, db: Session = Depends(get_db), user: CurrentUser = Depends(require_permission("purchasing:reports:read"))):
    out=io.StringIO(); writer=csv.writer(out)
    if resource=="suppliers":
        writer.writerow(["name","tax_id","contact","phone","email","status","payment_terms_days"])
        for x in db.scalars(select(Supplier).where(Supplier.company_id==user.active_company_id).order_by(Supplier.name)).all():
            writer.writerow([x.name,x.tax_id,x.contact_name,x.phone,x.email,x.status,x.payment_terms_days])
    elif resource=="purchase-orders":
        writer.writerow(["po_number","supplier_id","status","currency","total","paid","payment_status","expected_delivery_date"])
        for x in db.scalars(select(PurchaseOrder).where(PurchaseOrder.company_id==user.active_company_id).order_by(PurchaseOrder.created_at.desc())).all():
            writer.writerow([x.po_number,x.supplier_id,x.status,x.currency,x.total_amount,x.amount_paid,x.payment_status,x.expected_delivery_date])
    else: raise NotFoundError("Export resource not found")
    return Response(content=("\ufeff"+out.getvalue()).encode("utf-8"),media_type="text/csv",
                    headers={"Content-Disposition":f'attachment; filename="{resource}.csv"'})
