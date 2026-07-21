"""Tests for the Purchasing module's Purchase Order lifecycle: creation,
editing, status transitions, and receiving (including real Catalog slab
creation on receipt)."""
import uuid


def test_create_purchase_order_computes_totals(app_client, owner_headers, supplier, material):
    resp = app_client.post(
        "/api/v1/purchasing/purchase-orders",
        headers=owner_headers,
        json={
            "supplier_id": supplier["id"],
            "lines": [
                {"material_id": str(material.id), "description": "Slab A", "quantity": "4", "unit_cost": "100.00"},
                {"description": "Freight", "quantity": "1", "unit_cost": "50.00"},
            ],
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "draft"
    assert body["po_number"].startswith("PO-")
    assert body["subtotal_amount"] == "450.00"
    assert body["total_amount"] == "450.00"

    lines = app_client.get(f"/api/v1/purchasing/purchase-orders/{body['id']}/lines", headers=owner_headers).json()
    assert len(lines["items"]) == 2
    assert lines["items"][0]["line_total"] == "400.00"


def test_create_purchase_order_requires_at_least_one_line(app_client, owner_headers, supplier):
    resp = app_client.post(
        "/api/v1/purchasing/purchase-orders",
        headers=owner_headers,
        json={"supplier_id": supplier["id"], "lines": []},
    )
    assert resp.status_code == 422, resp.text


def test_create_purchase_order_against_hidden_supplier_rejected(app_client, owner_headers, supplier):
    app_client.patch(
        f"/api/v1/purchasing/suppliers/{supplier['id']}", headers=owner_headers, json={"status": "hidden"}
    )
    resp = app_client.post(
        "/api/v1/purchasing/purchase-orders",
        headers=owner_headers,
        json={"supplier_id": supplier["id"], "lines": [{"description": "X", "quantity": "1", "unit_cost": "1"}]},
    )
    assert resp.status_code == 422, resp.text


def test_create_purchase_order_unknown_supplier_returns_404(app_client, owner_headers):
    resp = app_client.post(
        "/api/v1/purchasing/purchase-orders",
        headers=owner_headers,
        json={"supplier_id": str(uuid.uuid4()), "lines": [{"description": "X", "quantity": "1", "unit_cost": "1"}]},
    )
    assert resp.status_code == 404


def test_update_purchase_order_only_while_draft(app_client, owner_headers, supplier):
    po = app_client.post(
        "/api/v1/purchasing/purchase-orders",
        headers=owner_headers,
        json={"supplier_id": supplier["id"], "lines": [{"description": "X", "quantity": "1", "unit_cost": "1"}]},
    ).json()

    ok = app_client.patch(
        f"/api/v1/purchasing/purchase-orders/{po['id']}", headers=owner_headers, json={"notes": "urgent"}
    )
    assert ok.status_code == 200
    assert ok.json()["notes"] == "urgent"

    app_client.post(f"/api/v1/purchasing/purchase-orders/{po['id']}/status", headers=owner_headers, json={"status": "sent"})
    blocked = app_client.patch(
        f"/api/v1/purchasing/purchase-orders/{po['id']}", headers=owner_headers, json={"notes": "too late"}
    )
    assert blocked.status_code == 422, blocked.text


def test_purchase_order_status_transitions(app_client, owner_headers, supplier):
    po = app_client.post(
        "/api/v1/purchasing/purchase-orders",
        headers=owner_headers,
        json={"supplier_id": supplier["id"], "lines": [{"description": "X", "quantity": "1", "unit_cost": "1"}]},
    ).json()

    # draft -> confirmed directly is not a legal transition
    illegal = app_client.post(
        f"/api/v1/purchasing/purchase-orders/{po['id']}/status", headers=owner_headers, json={"status": "confirmed"}
    )
    assert illegal.status_code == 422, illegal.text

    # partially_received/received are not manually settable at all
    not_manual = app_client.post(
        f"/api/v1/purchasing/purchase-orders/{po['id']}/status", headers=owner_headers, json={"status": "received"}
    )
    assert not_manual.status_code == 400, not_manual.text

    sent = app_client.post(
        f"/api/v1/purchasing/purchase-orders/{po['id']}/status", headers=owner_headers, json={"status": "sent"}
    )
    assert sent.status_code == 200
    assert sent.json()["status"] == "sent"

    cancelled = app_client.post(
        f"/api/v1/purchasing/purchase-orders/{po['id']}/status",
        headers=owner_headers,
        json={"status": "cancelled", "cancelled_reason": "Supplier out of stock"},
    )
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "cancelled"
    assert cancelled.json()["cancelled_reason"] == "Supplier out of stock"

    # cancelled is terminal
    dead = app_client.post(
        f"/api/v1/purchasing/purchase-orders/{po['id']}/status", headers=owner_headers, json={"status": "sent"}
    )
    assert dead.status_code == 422, dead.text


def test_receive_full_quantity_creates_slab_and_marks_order_received(
    app_client, owner_headers, db_session, confirmed_po, warehouse
):
    from modules.catalog.infrastructure.models.slab import Slab

    line_id = app_client.get(
        f"/api/v1/purchasing/purchase-orders/{confirmed_po['id']}/lines", headers=owner_headers
    ).json()["items"][0]["id"]

    resp = app_client.post(
        f"/api/v1/purchasing/purchase-orders/{confirmed_po['id']}/lines/{line_id}/receive",
        headers=owner_headers,
        json={
            "quantity_received": "10",
            "warehouse_id": str(warehouse.id),
            "slab_number": "SLB-PO-0001",
            "length_mm": "3200",
            "width_mm": "1600",
        },
    )
    assert resp.status_code == 200, resp.text
    receipt = resp.json()
    assert receipt["quantity_received"] == "10.000"
    assert receipt["slab_id"] is not None

    slab = db_session.get(Slab, receipt["slab_id"])
    assert slab is not None
    assert slab.status == "available"
    assert slab.slab_number == "SLB-PO-0001"

    order = app_client.get(f"/api/v1/purchasing/purchase-orders/{confirmed_po['id']}", headers=owner_headers).json()
    assert order["status"] == "received"

    lines = app_client.get(
        f"/api/v1/purchasing/purchase-orders/{confirmed_po['id']}/lines", headers=owner_headers
    ).json()
    assert lines["items"][0]["quantity_received"] == "10.000"


def test_receive_partial_quantity_marks_order_partially_received(app_client, owner_headers, confirmed_po):
    line_id = app_client.get(
        f"/api/v1/purchasing/purchase-orders/{confirmed_po['id']}/lines", headers=owner_headers
    ).json()["items"][0]["id"]

    resp = app_client.post(
        f"/api/v1/purchasing/purchase-orders/{confirmed_po['id']}/lines/{line_id}/receive",
        headers=owner_headers,
        json={"quantity_received": "4"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["slab_id"] is None  # no warehouse/slab details supplied -- receipt-only, no slab created

    order = app_client.get(f"/api/v1/purchasing/purchase-orders/{confirmed_po['id']}", headers=owner_headers).json()
    assert order["status"] == "partially_received"


def test_receive_more_than_remaining_quantity_rejected(app_client, owner_headers, confirmed_po):
    line_id = app_client.get(
        f"/api/v1/purchasing/purchase-orders/{confirmed_po['id']}/lines", headers=owner_headers
    ).json()["items"][0]["id"]

    resp = app_client.post(
        f"/api/v1/purchasing/purchase-orders/{confirmed_po['id']}/lines/{line_id}/receive",
        headers=owner_headers,
        json={"quantity_received": "11"},
    )
    assert resp.status_code == 422, resp.text


def test_receive_against_draft_order_rejected(app_client, owner_headers, supplier, material):
    po = app_client.post(
        "/api/v1/purchasing/purchase-orders",
        headers=owner_headers,
        json={
            "supplier_id": supplier["id"],
            "lines": [{"material_id": str(material.id), "description": "X", "quantity": "5", "unit_cost": "10"}],
        },
    ).json()
    line_id = app_client.get(
        f"/api/v1/purchasing/purchase-orders/{po['id']}/lines", headers=owner_headers
    ).json()["items"][0]["id"]

    resp = app_client.post(
        f"/api/v1/purchasing/purchase-orders/{po['id']}/lines/{line_id}/receive",
        headers=owner_headers,
        json={"quantity_received": "1"},
    )
    assert resp.status_code == 422, resp.text


def test_receive_with_slab_details_but_no_material_on_line_rejected(app_client, owner_headers, supplier, warehouse):
    po = app_client.post(
        "/api/v1/purchasing/purchase-orders",
        headers=owner_headers,
        json={"supplier_id": supplier["id"], "lines": [{"description": "Delivery fee", "quantity": "1", "unit_cost": "50"}]},
    ).json()
    for status in ("sent", "confirmed"):
        app_client.post(f"/api/v1/purchasing/purchase-orders/{po['id']}/status", headers=owner_headers, json={"status": status})
    line_id = app_client.get(f"/api/v1/purchasing/purchase-orders/{po['id']}/lines", headers=owner_headers).json()["items"][0]["id"]

    resp = app_client.post(
        f"/api/v1/purchasing/purchase-orders/{po['id']}/lines/{line_id}/receive",
        headers=owner_headers,
        json={"quantity_received": "1", "warehouse_id": str(warehouse.id), "slab_number": "SLB-X", "length_mm": "100", "width_mm": "100"},
    )
    assert resp.status_code == 422, resp.text


def test_list_goods_receipts_for_order(app_client, owner_headers, confirmed_po):
    line_id = app_client.get(
        f"/api/v1/purchasing/purchase-orders/{confirmed_po['id']}/lines", headers=owner_headers
    ).json()["items"][0]["id"]
    app_client.post(
        f"/api/v1/purchasing/purchase-orders/{confirmed_po['id']}/lines/{line_id}/receive",
        headers=owner_headers,
        json={"quantity_received": "3"},
    )
    app_client.post(
        f"/api/v1/purchasing/purchase-orders/{confirmed_po['id']}/lines/{line_id}/receive",
        headers=owner_headers,
        json={"quantity_received": "2"},
    )

    receipts = app_client.get(
        f"/api/v1/purchasing/purchase-orders/{confirmed_po['id']}/receipts", headers=owner_headers
    ).json()
    assert len(receipts["items"]) == 2
    assert {r["quantity_received"] for r in receipts["items"]} == {"3.000", "2.000"}
