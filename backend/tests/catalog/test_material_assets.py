"""Images and documents are uploaded via the shared core /documents
endpoint (same storage pipeline as CRM attachments), then linked to a
Material via the catalog-specific join endpoints."""
import uuid


def _material(client, headers):
    brand = client.post("/api/v1/catalog/brands", headers=headers, json={"name": "NEOLITH"}).json()
    return client.post(
        "/api/v1/catalog/materials", headers=headers, json={"brand_id": brand["id"], "name": "Calacatta Gold"}
    ).json()


def _upload_document(client, headers, material_id, filename="slab.jpg", content_type="image/jpeg"):
    response = client.post(
        "/api/v1/core/documents",
        headers=headers,
        data={"module": "catalog", "related_entity_type": "material", "related_entity_id": material_id},
        files={"file": (filename, b"fake binary content", content_type)},
    )
    assert response.status_code == 200, response.text
    return response.json()["id"]


def test_add_material_image(app_client, owner_headers):
    material = _material(app_client, owner_headers)
    document_id = _upload_document(app_client, owner_headers, material["id"])

    response = app_client.post(
        f"/api/v1/catalog/materials/{material['id']}/images",
        headers=owner_headers,
        json={"document_id": document_id, "image_type": "gallery", "sort_order": 0},
    )
    assert response.status_code == 200, response.text
    assert response.json()["image_type"] == "gallery"

    listed = app_client.get(f"/api/v1/catalog/materials/{material['id']}/images", headers=owner_headers).json()
    assert len(listed["items"]) == 1


def test_add_material_image_supports_bookmatch_pair(app_client, owner_headers):
    material = _material(app_client, owner_headers)
    left_doc = _upload_document(app_client, owner_headers, material["id"], "left.jpg")
    right_doc = _upload_document(app_client, owner_headers, material["id"], "right.jpg")

    app_client.post(
        f"/api/v1/catalog/materials/{material['id']}/images",
        headers=owner_headers,
        json={"document_id": left_doc, "image_type": "bookmatch_left"},
    )
    app_client.post(
        f"/api/v1/catalog/materials/{material['id']}/images",
        headers=owner_headers,
        json={"document_id": right_doc, "image_type": "bookmatch_right"},
    )

    listed = app_client.get(f"/api/v1/catalog/materials/{material['id']}/images", headers=owner_headers).json()
    image_types = {item["image_type"] for item in listed["items"]}
    assert image_types == {"bookmatch_left", "bookmatch_right"}


def test_add_material_image_rejects_invalid_image_type(app_client, owner_headers):
    material = _material(app_client, owner_headers)
    document_id = _upload_document(app_client, owner_headers, material["id"])

    response = app_client.post(
        f"/api/v1/catalog/materials/{material['id']}/images",
        headers=owner_headers,
        json={"document_id": document_id, "image_type": "panorama"},
    )
    assert response.status_code in (400, 422)


def test_add_material_document_technical_pdf(app_client, owner_headers):
    material = _material(app_client, owner_headers)
    document_id = _upload_document(app_client, owner_headers, material["id"], "datasheet.pdf", "application/pdf")

    response = app_client.post(
        f"/api/v1/catalog/materials/{material['id']}/documents",
        headers=owner_headers,
        json={"document_id": document_id, "document_type": "technical_pdf"},
    )
    assert response.status_code == 200, response.text
    assert response.json()["document_type"] == "technical_pdf"

    listed = app_client.get(f"/api/v1/catalog/materials/{material['id']}/documents", headers=owner_headers).json()
    assert len(listed["items"]) == 1


def test_add_material_document_rejects_invalid_document_type(app_client, owner_headers):
    material = _material(app_client, owner_headers)
    document_id = _upload_document(app_client, owner_headers, material["id"], "x.pdf", "application/pdf")

    response = app_client.post(
        f"/api/v1/catalog/materials/{material['id']}/documents",
        headers=owner_headers,
        json={"document_id": document_id, "document_type": "warranty_card"},
    )
    assert response.status_code in (400, 422)


def test_material_assets_require_existing_material(app_client, owner_headers):
    document_id = _upload_document(app_client, owner_headers, str(uuid.uuid4()))
    response = app_client.post(
        f"/api/v1/catalog/materials/{uuid.uuid4()}/images",
        headers=owner_headers,
        json={"document_id": document_id, "image_type": "gallery"},
    )
    assert response.status_code == 404
