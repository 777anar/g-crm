"""Tests for the Offcut Library search surface (Phase 2 requirement #3)."""


def _brand_and_material(client, headers, brand_name="NEOLITH", material_name="Calacatta Gold", finish="Polished", thickness_mm="20"):
    brand = client.post("/api/v1/catalog/brands", headers=headers, json={"name": brand_name}).json()
    material = client.post(
        "/api/v1/catalog/materials",
        headers=headers,
        json={"brand_id": brand["id"], "name": material_name, "finish": finish, "thickness_mm": thickness_mm},
    ).json()
    return brand, material


def _warehouse(client, headers, name="Main Warehouse"):
    return client.post("/api/v1/catalog/warehouses", headers=headers, json={"name": name}).json()


def _make_offcut(client, headers, material, warehouse, slab_number, length_mm="800", width_mm="600"):
    parent = client.post(
        "/api/v1/catalog/slabs", headers=headers,
        json={"material_id": material["id"], "warehouse_id": warehouse["id"], "slab_number": f"PARENT-{slab_number}"},
    ).json()
    client.patch(f"/api/v1/catalog/slabs/{parent['id']}/status", headers=headers, json={"status": "reserved"})
    client.patch(f"/api/v1/catalog/slabs/{parent['id']}/status", headers=headers, json={"status": "in_production"})
    return client.post(
        f"/api/v1/catalog/slabs/{parent['id']}/offcuts", headers=headers,
        json={"warehouse_id": warehouse["id"], "slab_number": slab_number, "length_mm": length_mm, "width_mm": width_mm},
    ).json()


def test_offcut_library_only_lists_available_offcuts(app_client, owner_headers):
    _, material = _brand_and_material(app_client, owner_headers)
    warehouse = _warehouse(app_client, owner_headers)
    offcut = _make_offcut(app_client, owner_headers, material, warehouse, "LIB-1")

    # A regular (non-offcut) slab must never show up in the library.
    app_client.post(
        "/api/v1/catalog/slabs", headers=owner_headers,
        json={"material_id": material["id"], "warehouse_id": warehouse["id"], "slab_number": "REGULAR-1"},
    )

    resp = app_client.get("/api/v1/catalog/slabs/offcuts", headers=owner_headers)
    assert resp.status_code == 200, resp.text
    items = resp.json()["items"]
    assert len(items) == 1
    assert items[0]["id"] == offcut["id"]
    assert items[0]["is_offcut"] is True


def test_offcut_library_filters_by_material(app_client, owner_headers):
    _, material_a = _brand_and_material(app_client, owner_headers, "NEOLITH", "Material A")
    _, material_b = _brand_and_material(app_client, owner_headers, "NEOLITH", "Material B")
    warehouse = _warehouse(app_client, owner_headers)
    _make_offcut(app_client, owner_headers, material_a, warehouse, "MAT-A-OFFCUT")
    _make_offcut(app_client, owner_headers, material_b, warehouse, "MAT-B-OFFCUT")

    resp = app_client.get(
        "/api/v1/catalog/slabs/offcuts", headers=owner_headers, params={"material_id": material_a["id"]}
    )
    items = resp.json()["items"]
    assert len(items) == 1
    assert items[0]["slab_number"] == "MAT-A-OFFCUT"


def test_offcut_library_filters_by_thickness_and_finish(app_client, owner_headers):
    _, polished = _brand_and_material(app_client, owner_headers, "NEOLITH", "Polished Spec", finish="Polished", thickness_mm="20")
    _, honed = _brand_and_material(app_client, owner_headers, "NEOLITH", "Honed Spec", finish="Honed", thickness_mm="30")
    warehouse = _warehouse(app_client, owner_headers)
    _make_offcut(app_client, owner_headers, polished, warehouse, "POLISHED-OFFCUT")
    _make_offcut(app_client, owner_headers, honed, warehouse, "HONED-OFFCUT")

    resp = app_client.get(
        "/api/v1/catalog/slabs/offcuts", headers=owner_headers, params={"thickness_mm": "30", "finish": "Honed"}
    )
    items = resp.json()["items"]
    assert len(items) == 1
    assert items[0]["slab_number"] == "HONED-OFFCUT"


def test_offcut_library_filters_by_minimum_dimensions_and_area(app_client, owner_headers):
    _, material = _brand_and_material(app_client, owner_headers)
    warehouse = _warehouse(app_client, owner_headers)
    _make_offcut(app_client, owner_headers, material, warehouse, "SMALL-OFFCUT", "400", "300")
    _make_offcut(app_client, owner_headers, material, warehouse, "BIG-OFFCUT", "1200", "900")

    by_dimension = app_client.get(
        "/api/v1/catalog/slabs/offcuts", headers=owner_headers,
        params={"min_length_mm": "1000", "min_width_mm": "800"},
    ).json()["items"]
    assert len(by_dimension) == 1
    assert by_dimension[0]["slab_number"] == "BIG-OFFCUT"

    by_area = app_client.get(
        "/api/v1/catalog/slabs/offcuts", headers=owner_headers, params={"min_area_m2": "1.0"}
    ).json()["items"]
    assert len(by_area) == 1
    assert by_area[0]["slab_number"] == "BIG-OFFCUT"


def test_offcut_library_search_by_slab_number(app_client, owner_headers):
    _, material = _brand_and_material(app_client, owner_headers)
    warehouse = _warehouse(app_client, owner_headers)
    _make_offcut(app_client, owner_headers, material, warehouse, "FINDME-OFFCUT")

    resp = app_client.get("/api/v1/catalog/slabs/offcuts", headers=owner_headers, params={"search": "FINDME"})
    assert len(resp.json()["items"]) == 1


def test_offcut_library_excludes_reserved_or_consumed_offcuts(app_client, owner_headers):
    _, material = _brand_and_material(app_client, owner_headers)
    warehouse = _warehouse(app_client, owner_headers)
    offcut = _make_offcut(app_client, owner_headers, material, warehouse, "RESERVED-OFFCUT")

    app_client.patch(f"/api/v1/catalog/slabs/{offcut['id']}/status", headers=owner_headers, json={"status": "reserved"})

    resp = app_client.get("/api/v1/catalog/slabs/offcuts", headers=owner_headers)
    assert resp.json()["items"] == []
