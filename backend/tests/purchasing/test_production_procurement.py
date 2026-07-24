"""End-to-end production Purchasing capabilities added in Version 2.41."""
from decimal import Decimal


def _create_po(client, headers, supplier, material):
    return client.post("/api/v1/purchasing/purchase-orders", headers=headers, json={"supplier_id":supplier["id"],
        "lines":[{"material_id":str(material.id),"description":"Stone slab","quantity":"2","unit":"slab","unit_cost":"100"}]}).json()


def test_supplier_contacts_and_metrics(app_client, owner_headers, supplier):
    contact=app_client.post(f"/api/v1/purchasing/suppliers/{supplier['id']}/contacts",headers=owner_headers,
        json={"name":"Leyla Aliyeva","email":"leyla@example.com","is_primary":True})
    assert contact.status_code==200,contact.text
    rows=app_client.get(f"/api/v1/purchasing/suppliers/{supplier['id']}/contacts",headers=owner_headers)
    assert rows.status_code==200 and rows.json()[0]["is_primary"] is True
    metrics=app_client.get(f"/api/v1/purchasing/suppliers/{supplier['id']}/metrics",headers=owner_headers)
    assert metrics.status_code==200 and metrics.json()["total_orders"]==0


def test_rfq_to_approved_purchase_order(app_client, owner_headers, supplier, material):
    rfq=app_client.post("/api/v1/purchasing/rfqs",headers=owner_headers,json={"supplier_id":supplier["id"],
        "lines":[{"material_id":str(material.id),"description":"Two slabs","quantity":"2","unit":"slab","quoted_unit_cost":"125"}]})
    assert rfq.status_code==200,rfq.text
    rid=rfq.json()["id"]
    assert app_client.post(f"/api/v1/purchasing/rfqs/{rid}/status",headers=owner_headers,json={"status":"sent"}).status_code==200
    quoted=app_client.post(f"/api/v1/purchasing/rfqs/{rid}/status",headers=owner_headers,json={"status":"quoted","quoted_total":"250"})
    assert quoted.status_code==200
    po=app_client.post(f"/api/v1/purchasing/rfqs/{rid}/convert",headers=owner_headers)
    assert po.status_code==200,po.text
    assert po.json()["rfq_id"]==rid and po.json()["total_amount"]=="250.00"
    for status in ("pending_approval","approved"):
        response=app_client.post(f"/api/v1/purchasing/purchase-orders/{po.json()['id']}/status",headers=owner_headers,json={"status":status,"approval_notes":"Budget checked"})
        assert response.status_code==200,response.text
    assert response.json()["approved_by"] is not None


def test_partial_receiving_return_and_stock_sync(app_client, owner_headers, supplier, material, warehouse, db_session):
    po=_create_po(app_client,owner_headers,supplier,material)
    for status in ("pending_approval","approved","sent","confirmed"):
        app_client.post(f"/api/v1/purchasing/purchase-orders/{po['id']}/status",headers=owner_headers,json={"status":status})
    line=app_client.get(f"/api/v1/purchasing/purchase-orders/{po['id']}/lines",headers=owner_headers).json()["items"][0]
    receipt=app_client.post(f"/api/v1/purchasing/purchase-orders/{po['id']}/lines/{line['id']}/receive",headers=owner_headers,
        json={"quantity_received":"1","warehouse_id":str(warehouse.id),"slab_number":"RET-001","length_mm":"3200","width_mm":"1600"})
    assert receipt.status_code==200,receipt.text
    ret=app_client.post("/api/v1/purchasing/returns",headers=owner_headers,json={"purchase_order_id":po["id"],"reason":"Surface damage",
        "lines":[{"goods_receipt_id":receipt.json()["id"],"quantity":"1"}]})
    assert ret.status_code==200,ret.text
    completed=app_client.post(f"/api/v1/purchasing/returns/{ret.json()['id']}/complete",headers=owner_headers)
    assert completed.status_code==200 and completed.json()["status"]=="completed"
    from modules.catalog.infrastructure.models.slab import Slab
    assert db_session.get(Slab,receipt.json()["slab_id"]).status=="scrap"


def test_payment_dashboard_and_exports(app_client, owner_headers, supplier, material):
    po=_create_po(app_client,owner_headers,supplier,material)
    paid=app_client.post(f"/api/v1/purchasing/purchase-orders/{po['id']}/payment",headers=owner_headers,
        json={"amount_paid":"50","payment_due_date":"2026-08-01"})
    assert paid.status_code==200 and paid.json()["payment_status"]=="partially_paid"
    dashboard=app_client.get("/api/v1/purchasing/dashboard",headers=owner_headers)
    assert dashboard.status_code==200 and Decimal(dashboard.json()["outstanding_payables"])==Decimal("150")
    for resource in ("suppliers","purchase-orders"):
        result=app_client.get(f"/api/v1/purchasing/export/{resource}",headers=owner_headers)
        assert result.status_code==200 and "text/csv" in result.headers["content-type"]


def test_viewer_cannot_mutate_procurement(app_client, viewer_headers, supplier):
    assert app_client.post(f"/api/v1/purchasing/suppliers/{supplier['id']}/contacts",headers=viewer_headers,
        json={"name":"Blocked"}).status_code==403
    assert app_client.post("/api/v1/purchasing/rfqs",headers=viewer_headers,json={"supplier_id":supplier["id"],
        "lines":[{"description":"x","quantity":"1"}]}).status_code==403


def test_purchase_order_document_attachment(app_client, owner_headers, owner_user, company, supplier, material, db_session):
    from core.storage.models import Document
    po=_create_po(app_client,owner_headers,supplier,material)
    doc=Document(company_id=company.id,module="purchasing",related_entity_type="purchase_order",
        related_entity_id=po["id"],storage_path="test/po.pdf",mime_type="application/pdf",uploaded_by=owner_user.id)
    db_session.add(doc);db_session.commit()
    attached=app_client.post("/api/v1/purchasing/attachments",headers=owner_headers,json={"entity_type":"purchase_order",
        "entity_id":po["id"],"document_id":str(doc.id),"label":"Supplier confirmation"})
    assert attached.status_code==200,attached.text
    rows=app_client.get("/api/v1/purchasing/attachments",headers=owner_headers,
        params={"entity_type":"purchase_order","entity_id":po["id"]})
    assert rows.status_code==200 and rows.json()[0]["document_id"]==str(doc.id)
