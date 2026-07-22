"""Tests for Material Reservation and offcut tracking (Phase 1: Stone
Fabrication Workflow -- Purchasing -> Inventory -> Production)."""
import uuid


def _brand_and_material(client, headers, brand_name="NEOLITH", material_name="Calacatta Gold"):
    brand = client.post("/api/v1/catalog/brands", headers=headers, json={"name": brand_name}).json()
    material = client.post(
        "/api/v1/catalog/materials", headers=headers, json={"brand_id": brand["id"], "name": material_name}
    ).json()
    return brand, material


def _warehouse(client, headers, name="Baku Main Warehouse"):
    return client.post("/api/v1/catalog/warehouses", headers=headers, json={"name": name}).json()


def _slab(client, headers, material, warehouse, slab_number="SL-R001", status=None):
    payload = {"material_id": material["id"], "warehouse_id": warehouse["id"], "slab_number": slab_number}
    if status:
        payload["status"] = status
    return client.post("/api/v1/catalog/slabs", headers=headers, json=payload).json()


def test_reserve_slab_moves_status_and_creates_reservation(app_client, owner_headers):
    _, material = _brand_and_material(app_client, owner_headers)
    warehouse = _warehouse(app_client, owner_headers)
    slab = _slab(app_client, owner_headers, material, warehouse)
    order_id = str(uuid.uuid4())
    order_item_id = str(uuid.uuid4())

    resp = app_client.post(
        f"/api/v1/catalog/slabs/{slab['id']}/reserve",
        headers=owner_headers,
        json={"order_id": order_id, "order_item_id": order_item_id},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "active"
    assert body["order_id"] == order_id
    assert body["order_item_id"] == order_item_id

    slab_after = app_client.get(f"/api/v1/catalog/slabs/{slab['id']}", headers=owner_headers).json()
    assert slab_after["status"] == "reserved"


def test_reserve_slab_twice_for_same_item_is_idempotent(app_client, owner_headers):
    _, material = _brand_and_material(app_client, owner_headers)
    warehouse = _warehouse(app_client, owner_headers)
    slab = _slab(app_client, owner_headers, material, warehouse)
    order_id = str(uuid.uuid4())
    order_item_id = str(uuid.uuid4())

    first = app_client.post(
        f"/api/v1/catalog/slabs/{slab['id']}/reserve",
        headers=owner_headers,
        json={"order_id": order_id, "order_item_id": order_item_id},
    )
    second = app_client.post(
        f"/api/v1/catalog/slabs/{slab['id']}/reserve",
        headers=owner_headers,
        json={"order_id": order_id, "order_item_id": order_item_id},
    )
    assert second.status_code == 200, second.text
    assert second.json()["id"] == first.json()["id"]


def test_reserve_slab_already_reserved_for_another_item_returns_409(app_client, owner_headers):
    _, material = _brand_and_material(app_client, owner_headers)
    warehouse = _warehouse(app_client, owner_headers)
    slab = _slab(app_client, owner_headers, material, warehouse)

    app_client.post(
        f"/api/v1/catalog/slabs/{slab['id']}/reserve",
        headers=owner_headers,
        json={"order_id": str(uuid.uuid4()), "order_item_id": str(uuid.uuid4())},
    )

    conflict = app_client.post(
        f"/api/v1/catalog/slabs/{slab['id']}/reserve",
        headers=owner_headers,
        json={"order_id": str(uuid.uuid4()), "order_item_id": str(uuid.uuid4())},
    )
    assert conflict.status_code == 409, conflict.text


def test_reserve_slab_not_available_returns_409(app_client, owner_headers):
    _, material = _brand_and_material(app_client, owner_headers)
    warehouse = _warehouse(app_client, owner_headers)
    slab = _slab(app_client, owner_headers, material, warehouse, status="scrap")

    resp = app_client.post(
        f"/api/v1/catalog/slabs/{slab['id']}/reserve",
        headers=owner_headers,
        json={"order_id": str(uuid.uuid4()), "order_item_id": str(uuid.uuid4())},
    )
    assert resp.status_code == 409, resp.text


def test_release_reservation_returns_slab_to_available(app_client, owner_headers):
    _, material = _brand_and_material(app_client, owner_headers)
    warehouse = _warehouse(app_client, owner_headers)
    slab = _slab(app_client, owner_headers, material, warehouse)

    reservation = app_client.post(
        f"/api/v1/catalog/slabs/{slab['id']}/reserve",
        headers=owner_headers,
        json={"order_id": str(uuid.uuid4()), "order_item_id": str(uuid.uuid4())},
    ).json()

    released = app_client.post(
        f"/api/v1/catalog/slabs/reservations/{reservation['id']}/release", headers=owner_headers
    )
    assert released.status_code == 200, released.text
    assert released.json()["status"] == "released"

    slab_after = app_client.get(f"/api/v1/catalog/slabs/{slab['id']}", headers=owner_headers).json()
    assert slab_after["status"] == "available"

    # Once released, the slab is reservable again (by anyone, including for
    # a brand new order item) -- the double-booking guard only blocks
    # concurrent *active* reservations.
    re_reserved = app_client.post(
        f"/api/v1/catalog/slabs/{slab['id']}/reserve",
        headers=owner_headers,
        json={"order_id": str(uuid.uuid4()), "order_item_id": str(uuid.uuid4())},
    )
    assert re_reserved.status_code == 200, re_reserved.text


def test_list_reservations_for_order(app_client, owner_headers):
    _, material = _brand_and_material(app_client, owner_headers)
    warehouse = _warehouse(app_client, owner_headers)
    slab_a = _slab(app_client, owner_headers, material, warehouse, "SL-ORD-A")
    slab_b = _slab(app_client, owner_headers, material, warehouse, "SL-ORD-B")
    order_id = str(uuid.uuid4())

    app_client.post(
        f"/api/v1/catalog/slabs/{slab_a['id']}/reserve",
        headers=owner_headers,
        json={"order_id": order_id, "order_item_id": str(uuid.uuid4())},
    )
    app_client.post(
        f"/api/v1/catalog/slabs/{slab_b['id']}/reserve",
        headers=owner_headers,
        json={"order_id": order_id, "order_item_id": str(uuid.uuid4())},
    )

    resp = app_client.get("/api/v1/catalog/reservations", headers=owner_headers, params={"order_id": order_id})
    assert resp.status_code == 200
    assert len(resp.json()["items"]) == 2


def test_slab_received_must_move_to_available_before_reservable(app_client, owner_headers):
    _, material = _brand_and_material(app_client, owner_headers)
    warehouse = _warehouse(app_client, owner_headers)
    slab = _slab(app_client, owner_headers, material, warehouse, status="received")

    # A `received` slab hasn't been shelved into stock yet -- can't reserve.
    blocked = app_client.post(
        f"/api/v1/catalog/slabs/{slab['id']}/reserve",
        headers=owner_headers,
        json={"order_id": str(uuid.uuid4()), "order_item_id": str(uuid.uuid4())},
    )
    assert blocked.status_code == 409, blocked.text

    shelved = app_client.patch(
        f"/api/v1/catalog/slabs/{slab['id']}/status", headers=owner_headers, json={"status": "available"}
    )
    assert shelved.status_code == 200
    assert shelved.json()["status"] == "available"

    now_reservable = app_client.post(
        f"/api/v1/catalog/slabs/{slab['id']}/reserve",
        headers=owner_headers,
        json={"order_id": str(uuid.uuid4()), "order_item_id": str(uuid.uuid4())},
    )
    assert now_reservable.status_code == 200, now_reservable.text


def test_received_slab_can_be_scrapped_directly(app_client, owner_headers):
    _, material = _brand_and_material(app_client, owner_headers)
    warehouse = _warehouse(app_client, owner_headers)
    slab = _slab(app_client, owner_headers, material, warehouse, status="received")

    resp = app_client.patch(
        f"/api/v1/catalog/slabs/{slab['id']}/status", headers=owner_headers, json={"status": "scrap"}
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "scrap"


def test_create_offcut_requires_slab_in_production(app_client, owner_headers):
    _, material = _brand_and_material(app_client, owner_headers)
    warehouse = _warehouse(app_client, owner_headers)
    slab = _slab(app_client, owner_headers, material, warehouse)  # status: available

    resp = app_client.post(
        f"/api/v1/catalog/slabs/{slab['id']}/offcuts",
        headers=owner_headers,
        json={"warehouse_id": warehouse["id"], "slab_number": "SL-OFFCUT-1"},
    )
    assert resp.status_code == 422, resp.text


def test_create_offcut_from_in_production_slab(app_client, owner_headers):
    _, material = _brand_and_material(app_client, owner_headers)
    warehouse = _warehouse(app_client, owner_headers)
    slab = _slab(app_client, owner_headers, material, warehouse)
    app_client.patch(f"/api/v1/catalog/slabs/{slab['id']}/status", headers=owner_headers, json={"status": "reserved"})
    app_client.patch(
        f"/api/v1/catalog/slabs/{slab['id']}/status", headers=owner_headers, json={"status": "in_production"}
    )

    resp = app_client.post(
        f"/api/v1/catalog/slabs/{slab['id']}/offcuts",
        headers=owner_headers,
        json={
            "warehouse_id": warehouse["id"],
            "slab_number": "SL-OFFCUT-2",
            "length_mm": "600",
            "width_mm": "400",
        },
    )
    assert resp.status_code == 200, resp.text
    offcut = resp.json()
    assert offcut["is_offcut"] is True
    assert offcut["parent_slab_id"] == slab["id"]
    assert offcut["status"] == "available"

    parent_after = app_client.get(f"/api/v1/catalog/slabs/{slab['id']}", headers=owner_headers).json()
    assert parent_after["status"] == "offcut_created"

    # The offcut itself is a completely normal, independently reservable slab.
    reserve = app_client.post(
        f"/api/v1/catalog/slabs/{offcut['id']}/reserve",
        headers=owner_headers,
        json={"order_id": str(uuid.uuid4()), "order_item_id": str(uuid.uuid4())},
    )
    assert reserve.status_code == 200, reserve.text


def test_reservations_are_scoped_to_company(app_client, owner_headers, db_session):
    """A slab reserved in one company must never be visible/reservable
    from another company's token -- reservation isolation follows the same
    company_id-scoping rule as every other cross-cutting concern."""
    from core.auth.models import ROLE_OWNER, User, UserCompanyRole
    from core.auth.security import create_access_token, hash_password
    from core.companies.models import Company

    _, material = _brand_and_material(app_client, owner_headers)
    warehouse = _warehouse(app_client, owner_headers)
    slab = _slab(app_client, owner_headers, material, warehouse)

    other_company = Company(name="Other Co", slug="other-co-reservations", enabled_modules=["catalog"])
    db_session.add(other_company)
    db_session.flush()
    other_user = User(email="owner@other-reservations.test", password_hash=hash_password("Password123!"), full_name="Other Owner")
    db_session.add(other_user)
    db_session.flush()
    db_session.add(UserCompanyRole(user_id=other_user.id, company_id=other_company.id, role=ROLE_OWNER))
    db_session.commit()
    other_headers = {
        "Authorization": f"Bearer {create_access_token(user_id=other_user.id, active_company_id=other_company.id, role=ROLE_OWNER)}"
    }

    cross_company = app_client.post(
        f"/api/v1/catalog/slabs/{slab['id']}/reserve",
        headers=other_headers,
        json={"order_id": str(uuid.uuid4()), "order_item_id": str(uuid.uuid4())},
    )
    assert cross_company.status_code == 404
