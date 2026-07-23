"""Phase 19 (Stone Fabrication Workflow, Phase 3): offcut dimension/area
plausibility validation, the sold-vs-consumed system boundary, and the
company-wide reservation browsing endpoint."""
import uuid


def _brand_and_material(client, headers, brand_name="NEOLITH", material_name="Calacatta Gold"):
    brand = client.post("/api/v1/catalog/brands", headers=headers, json={"name": brand_name}).json()
    material = client.post(
        "/api/v1/catalog/materials", headers=headers, json={"brand_id": brand["id"], "name": material_name}
    ).json()
    return brand, material


def _warehouse(client, headers, name="Baku Main Warehouse"):
    return client.post("/api/v1/catalog/warehouses", headers=headers, json={"name": name}).json()


def _slab(client, headers, material, warehouse, slab_number="SL-R001", **extra):
    payload = {"material_id": material["id"], "warehouse_id": warehouse["id"], "slab_number": slab_number, **extra}
    return client.post("/api/v1/catalog/slabs", headers=headers, json=payload).json()


def _slab_in_production(client, headers, material, warehouse, slab_number, length_mm=None, width_mm=None):
    extra = {}
    if length_mm is not None:
        extra["length_mm"] = length_mm
    if width_mm is not None:
        extra["width_mm"] = width_mm
    slab = _slab(client, headers, material, warehouse, slab_number, **extra)
    client.patch(f"/api/v1/catalog/slabs/{slab['id']}/status", headers=headers, json={"status": "reserved"})
    client.patch(f"/api/v1/catalog/slabs/{slab['id']}/status", headers=headers, json={"status": "in_production"})
    return slab


# ── Offcut dimension/area validation ────────────────────────────────────────


def test_offcut_larger_than_parent_is_rejected(app_client, owner_headers):
    _, material = _brand_and_material(app_client, owner_headers)
    warehouse = _warehouse(app_client, owner_headers)
    parent = _slab_in_production(
        app_client, owner_headers, material, warehouse, "SL-PARENT-1", length_mm="1000", width_mm="500"
    )

    resp = app_client.post(
        f"/api/v1/catalog/slabs/{parent['id']}/offcuts",
        headers=owner_headers,
        json={"warehouse_id": warehouse["id"], "slab_number": "SL-OFF-TOO-BIG", "length_mm": "1200", "width_mm": "500"},
    )
    assert resp.status_code == 422, resp.text


def test_offcut_that_fits_only_when_rotated_is_accepted(app_client, owner_headers):
    _, material = _brand_and_material(app_client, owner_headers)
    warehouse = _warehouse(app_client, owner_headers)
    parent = _slab_in_production(
        app_client, owner_headers, material, warehouse, "SL-PARENT-2", length_mm="1000", width_mm="500"
    )

    # 800x400 doesn't fit as length<=1000,width<=500 directly if swapped
    # incorrectly, but does fit the parent's bounding box when rotated
    # (400<=500, 800<=1000) -- a cut piece is routinely rotated relative to
    # the parent's own recorded length/width.
    resp = app_client.post(
        f"/api/v1/catalog/slabs/{parent['id']}/offcuts",
        headers=owner_headers,
        json={"warehouse_id": warehouse["id"], "slab_number": "SL-OFF-ROTATED", "length_mm": "400", "width_mm": "800"},
    )
    assert resp.status_code == 200, resp.text


def test_offcut_with_no_dimensions_recorded_skips_validation(app_client, owner_headers):
    _, material = _brand_and_material(app_client, owner_headers)
    warehouse = _warehouse(app_client, owner_headers)
    # Parent slab created with no length/width on file at all.
    parent = _slab_in_production(app_client, owner_headers, material, warehouse, "SL-PARENT-3")

    resp = app_client.post(
        f"/api/v1/catalog/slabs/{parent['id']}/offcuts",
        headers=owner_headers,
        json={"warehouse_id": warehouse["id"], "slab_number": "SL-OFF-NODIM", "length_mm": "5000", "width_mm": "5000"},
    )
    assert resp.status_code == 200, resp.text


# ── Sold vs. consumed system boundary ───────────────────────────────────────


def test_manual_patch_to_consumed_is_rejected(app_client, owner_headers):
    _, material = _brand_and_material(app_client, owner_headers)
    warehouse = _warehouse(app_client, owner_headers)
    slab = _slab_in_production(app_client, owner_headers, material, warehouse, "SL-CONSUME-1")

    resp = app_client.patch(
        f"/api/v1/catalog/slabs/{slab['id']}/status", headers=owner_headers, json={"status": "consumed"}
    )
    assert resp.status_code == 409, resp.text
    assert "system" in resp.json()["error"]["message"].lower() or "automatically" in resp.json()["error"]["message"].lower()


def test_selling_a_reserved_slab_releases_its_dangling_reservation(app_client, owner_headers):
    _, material = _brand_and_material(app_client, owner_headers)
    warehouse = _warehouse(app_client, owner_headers)
    slab = _slab(app_client, owner_headers, material, warehouse, "SL-SOLD-1")
    order_id = str(uuid.uuid4())
    order_item_id = str(uuid.uuid4())

    app_client.post(
        f"/api/v1/catalog/slabs/{slab['id']}/reserve",
        headers=owner_headers,
        json={"order_id": order_id, "order_item_id": order_item_id},
    )

    sold = app_client.patch(
        f"/api/v1/catalog/slabs/{slab['id']}/status", headers=owner_headers, json={"status": "sold"}
    )
    assert sold.status_code == 200, sold.text

    reservations = app_client.get(
        f"/api/v1/catalog/slabs/{slab['id']}/reservations", headers=owner_headers
    ).json()["items"]
    assert len(reservations) == 1
    assert reservations[0]["status"] == "released"
    assert reservations[0]["released_at"] is not None


def test_scrapping_an_in_production_slab_releases_its_dangling_reservation(app_client, owner_headers):
    _, material = _brand_and_material(app_client, owner_headers)
    warehouse = _warehouse(app_client, owner_headers)
    slab = _slab(app_client, owner_headers, material, warehouse, "SL-SCRAP-1")
    order_id = str(uuid.uuid4())
    order_item_id = str(uuid.uuid4())
    app_client.post(
        f"/api/v1/catalog/slabs/{slab['id']}/reserve",
        headers=owner_headers,
        json={"order_id": order_id, "order_item_id": order_item_id},
    )
    app_client.patch(f"/api/v1/catalog/slabs/{slab['id']}/status", headers=owner_headers, json={"status": "in_production"})

    scrapped = app_client.patch(
        f"/api/v1/catalog/slabs/{slab['id']}/status", headers=owner_headers, json={"status": "scrap"}
    )
    assert scrapped.status_code == 200, scrapped.text

    reservations = app_client.get(
        f"/api/v1/catalog/slabs/{slab['id']}/reservations", headers=owner_headers
    ).json()["items"]
    assert reservations[0]["status"] == "released"


# ── Company-wide reservation browsing ───────────────────────────────────────


def test_list_reservations_without_order_id_browses_the_whole_company(app_client, owner_headers):
    _, material = _brand_and_material(app_client, owner_headers)
    warehouse = _warehouse(app_client, owner_headers)
    slab_a = _slab(app_client, owner_headers, material, warehouse, "SL-BROWSE-A")
    slab_b = _slab(app_client, owner_headers, material, warehouse, "SL-BROWSE-B")

    app_client.post(
        f"/api/v1/catalog/slabs/{slab_a['id']}/reserve",
        headers=owner_headers,
        json={"order_id": str(uuid.uuid4()), "order_item_id": str(uuid.uuid4())},
    )
    app_client.post(
        f"/api/v1/catalog/slabs/{slab_b['id']}/reserve",
        headers=owner_headers,
        json={"order_id": str(uuid.uuid4()), "order_item_id": str(uuid.uuid4())},
    )

    resp = app_client.get("/api/v1/catalog/reservations", headers=owner_headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert len(body["items"]) == 2


def test_list_reservations_filters_by_status(app_client, owner_headers):
    _, material = _brand_and_material(app_client, owner_headers)
    warehouse = _warehouse(app_client, owner_headers)
    slab = _slab(app_client, owner_headers, material, warehouse, "SL-BROWSE-C")
    reservation = app_client.post(
        f"/api/v1/catalog/slabs/{slab['id']}/reserve",
        headers=owner_headers,
        json={"order_id": str(uuid.uuid4()), "order_item_id": str(uuid.uuid4())},
    ).json()
    app_client.post(f"/api/v1/catalog/slabs/reservations/{reservation['id']}/release", headers=owner_headers)

    active = app_client.get(
        "/api/v1/catalog/reservations", headers=owner_headers, params={"status": "active"}
    ).json()["items"]
    released = app_client.get(
        "/api/v1/catalog/reservations", headers=owner_headers, params={"status": "released"}
    ).json()["items"]
    assert active == []
    assert len(released) == 1
