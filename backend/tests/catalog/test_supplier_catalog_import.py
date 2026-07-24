"""Tests for the standardized supplier catalog import pipeline (Phase 20:
Advanced Cut Optimization & Supply Chain Intelligence) -- CSV import that
finds-or-creates Brands and upserts Materials/Thicknesses/Sizes."""


def _csv_bytes(text: str) -> bytes:
    return text.encode("utf-8")


def test_download_import_template(app_client, owner_headers):
    resp = app_client.get("/api/v1/catalog/materials/import/template", headers=owner_headers)
    assert resp.status_code == 200, resp.text
    assert resp.headers["content-type"].startswith("text/csv")
    assert "brand" in resp.text
    assert "material_name" in resp.text


def test_import_creates_brand_and_material_with_thicknesses_and_sizes(app_client, owner_headers):
    csv_content = (
        "brand,material_name,material_type,color,finish,country_of_origin,description,thicknesses_mm,sizes\n"
        'NEOLITH,Calacatta Gold,Sintered Stone,White,Polished,Spain,"Elegant surface","12;20","3200x1600mm"\n'
    )
    resp = app_client.post(
        "/api/v1/catalog/materials/import",
        headers=owner_headers,
        files={"file": ("catalog.csv", _csv_bytes(csv_content), "text/csv")},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["brands_created"] == 1
    assert body["materials_created"] == 1
    assert body["thicknesses_added"] == 2
    assert body["sizes_added"] == 1
    assert body["errors"] == []

    materials = app_client.get("/api/v1/catalog/materials", headers=owner_headers).json()["items"]
    assert any(m["name"] == "Calacatta Gold" for m in materials)

    brands = app_client.get("/api/v1/catalog/brands", headers=owner_headers).json()["items"]
    assert any(b["name"] == "NEOLITH" for b in brands)


def test_reimport_upserts_existing_brand_and_material_without_duplicating(app_client, owner_headers):
    first = (
        "brand,material_name,thicknesses_mm,sizes\n"
        'NEOLITH,Calacatta Gold,"12","3200x1600mm"\n'
    )
    app_client.post(
        "/api/v1/catalog/materials/import",
        headers=owner_headers,
        files={"file": ("catalog.csv", _csv_bytes(first), "text/csv")},
    )

    second = (
        "brand,material_name,color,thicknesses_mm,sizes\n"
        'neolith,calacatta gold,White,"12;20","3200x1600mm;3000x1400mm"\n'
    )
    resp = app_client.post(
        "/api/v1/catalog/materials/import",
        headers=owner_headers,
        files={"file": ("catalog2.csv", _csv_bytes(second), "text/csv")},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["brands_created"] == 0
    assert body["materials_created"] == 0
    assert body["materials_updated"] == 1
    assert body["thicknesses_added"] == 1
    assert body["sizes_added"] == 1

    brands = app_client.get("/api/v1/catalog/brands", headers=owner_headers).json()["items"]
    assert len([b for b in brands if b["name"].lower() == "neolith"]) == 1
    materials = app_client.get("/api/v1/catalog/materials", headers=owner_headers).json()["items"]
    assert len([m for m in materials if m["name"].lower() == "calacatta gold"]) == 1


def test_import_reports_row_errors_without_aborting_whole_file(app_client, owner_headers):
    csv_content = (
        "brand,material_name\n"
        ",Missing Brand Material\n"
        "NEOLITH,Valid Material\n"
    )
    resp = app_client.post(
        "/api/v1/catalog/materials/import",
        headers=owner_headers,
        files={"file": ("catalog.csv", _csv_bytes(csv_content), "text/csv")},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["materials_created"] == 1
    assert len(body["errors"]) == 1
    assert body["errors"][0]["row_number"] == 1


def test_import_missing_required_columns_returns_400(app_client, owner_headers):
    csv_content = "brand\nNEOLITH\n"
    resp = app_client.post(
        "/api/v1/catalog/materials/import",
        headers=owner_headers,
        files={"file": ("catalog.csv", _csv_bytes(csv_content), "text/csv")},
    )
    assert resp.status_code == 400, resp.text


def test_import_requires_write_permission(app_client, viewer_headers):
    csv_content = "brand,material_name\nNEOLITH,Calacatta Gold\n"
    resp = app_client.post(
        "/api/v1/catalog/materials/import",
        headers=viewer_headers,
        files={"file": ("catalog.csv", _csv_bytes(csv_content), "text/csv")},
    )
    assert resp.status_code == 403
