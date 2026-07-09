"""Tests for the Project workspace (Sprint 3): Rooms, Project Items, and
their Measurements/Drawings/Photos. Rooms/Items are project-planning records,
independent of any specific Quote version."""
import io

from core.audit.models import AuditLog
from core.auth.models import ROLE_OWNER, User, UserCompanyRole
from core.auth.security import create_access_token, hash_password
from core.companies.models import Company
from core.events.models import EventLogEntry


def _audit_actions(db_session, entity_type):
    return [r.action for r in db_session.query(AuditLog).filter(AuditLog.entity_type == entity_type).all()]


def _event_names(db_session):
    return [r.event_name for r in db_session.query(EventLogEntry).all()]


def _create_project(client, headers, customer_id):
    return client.post(
        "/api/v1/sales/projects",
        headers=headers,
        json={"customer_id": str(customer_id), "name": "Renovation"},
    ).json()


def _create_room(client, headers, project_id, room_type="kitchen"):
    return client.post(
        f"/api/v1/sales/projects/{project_id}/rooms",
        headers=headers,
        json={"room_type": room_type, "name": "Main Kitchen"},
    ).json()


def _create_item(client, headers, room_id, item_type="countertop"):
    return client.post(
        f"/api/v1/sales/rooms/{room_id}/items",
        headers=headers,
        json={"item_type": item_type, "quantity": "1"},
    ).json()


# ── Rooms ──────────────────────────────────────────────────────────────────────


def test_create_and_list_rooms(app_client, owner_headers, customer):
    project = _create_project(app_client, owner_headers, customer.id)
    resp = app_client.post(
        f"/api/v1/sales/projects/{project['id']}/rooms",
        headers=owner_headers,
        json={"room_type": "kitchen", "name": "Main Kitchen"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["room_type"] == "kitchen"

    list_resp = app_client.get(f"/api/v1/sales/projects/{project['id']}/rooms", headers=owner_headers)
    assert len(list_resp.json()["items"]) == 1


def test_room_invalid_type_rejected(app_client, owner_headers, customer):
    project = _create_project(app_client, owner_headers, customer.id)
    resp = app_client.post(
        f"/api/v1/sales/projects/{project['id']}/rooms",
        headers=owner_headers,
        json={"room_type": "spaceship"},
    )
    assert resp.status_code in (400, 422)


def test_update_and_delete_room(app_client, owner_headers, customer):
    project = _create_project(app_client, owner_headers, customer.id)
    room = _create_room(app_client, owner_headers, project["id"])

    resp = app_client.patch(f"/api/v1/sales/rooms/{room['id']}", headers=owner_headers, json={"name": "Kitchen v2"})
    assert resp.status_code == 200
    assert resp.json()["name"] == "Kitchen v2"

    del_resp = app_client.delete(f"/api/v1/sales/rooms/{room['id']}", headers=owner_headers)
    assert del_resp.status_code == 204
    list_resp = app_client.get(f"/api/v1/sales/projects/{project['id']}/rooms", headers=owner_headers)
    assert len(list_resp.json()["items"]) == 0


def test_deleting_room_cascades_to_items(app_client, owner_headers, customer):
    project = _create_project(app_client, owner_headers, customer.id)
    room = _create_room(app_client, owner_headers, project["id"])
    _create_item(app_client, owner_headers, room["id"])

    app_client.delete(f"/api/v1/sales/rooms/{room['id']}", headers=owner_headers)

    items_resp = app_client.get(f"/api/v1/sales/projects/{project['id']}/items", headers=owner_headers)
    assert len(items_resp.json()["items"]) == 0


def test_room_audit_and_events(app_client, owner_headers, customer, db_session):
    project = _create_project(app_client, owner_headers, customer.id)
    _create_room(app_client, owner_headers, project["id"])

    assert "room.created" in _audit_actions(db_session, "room")
    assert "RoomCreated" in _event_names(db_session)


# ── Project Items ──────────────────────────────────────────────────────────────


def test_create_and_list_project_items(app_client, owner_headers, customer):
    project = _create_project(app_client, owner_headers, customer.id)
    room = _create_room(app_client, owner_headers, project["id"])

    resp = app_client.post(
        f"/api/v1/sales/rooms/{room['id']}/items",
        headers=owner_headers,
        json={"item_type": "countertop", "name": "Main countertop", "quantity": "1.5"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["item_type"] == "countertop"
    assert body["unit"] == "m2"  # auto-filled default unit
    assert body["project_id"] == project["id"]  # denormalized from the room's project

    list_resp = app_client.get(f"/api/v1/sales/rooms/{room['id']}/items", headers=owner_headers)
    assert len(list_resp.json()["items"]) == 1

    project_items_resp = app_client.get(f"/api/v1/sales/projects/{project['id']}/items", headers=owner_headers)
    assert len(project_items_resp.json()["items"]) == 1


def test_project_item_invalid_type_rejected(app_client, owner_headers, customer):
    project = _create_project(app_client, owner_headers, customer.id)
    room = _create_room(app_client, owner_headers, project["id"])
    resp = app_client.post(
        f"/api/v1/sales/rooms/{room['id']}/items",
        headers=owner_headers,
        json={"item_type": "flying_carpet", "quantity": "1"},
    )
    assert resp.status_code in (400, 422)


def test_project_item_material_from_catalog(app_client, owner_headers, customer, material):
    project = _create_project(app_client, owner_headers, customer.id)
    room = _create_room(app_client, owner_headers, project["id"])
    resp = app_client.post(
        f"/api/v1/sales/rooms/{room['id']}/items",
        headers=owner_headers,
        json={"item_type": "countertop", "material_id": str(material.id), "quantity": "1"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["material_id"] == str(material.id)


def test_project_item_thickness_and_size_from_stone(app_client, owner_headers, customer, material):
    """Sprint 4: Brand -> Stone -> Thickness -> Size -- the Thickness/Size
    chosen for an item must be one of that Stone's own normalized options."""
    thickness = app_client.post(
        f"/api/v1/catalog/materials/{material.id}/thicknesses",
        headers=owner_headers,
        json={"thickness_mm": "20"},
    ).json()
    size = app_client.post(
        f"/api/v1/catalog/materials/{material.id}/sizes",
        headers=owner_headers,
        json={"dimensions": "3200x1600mm"},
    ).json()

    project = _create_project(app_client, owner_headers, customer.id)
    room = _create_room(app_client, owner_headers, project["id"])
    resp = app_client.post(
        f"/api/v1/sales/rooms/{room['id']}/items",
        headers=owner_headers,
        json={
            "item_type": "countertop",
            "material_id": str(material.id),
            "material_thickness_id": thickness["id"],
            "material_size_id": size["id"],
            "quantity": "1",
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["material_thickness_id"] == thickness["id"]
    assert body["material_size_id"] == size["id"]

    update_resp = app_client.patch(
        f"/api/v1/sales/project-items/{body['id']}",
        headers=owner_headers,
        json={"material_thickness_id": thickness["id"]},
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["material_thickness_id"] == thickness["id"]


def test_update_project_item_status(app_client, owner_headers, customer):
    project = _create_project(app_client, owner_headers, customer.id)
    room = _create_room(app_client, owner_headers, project["id"])
    item = _create_item(app_client, owner_headers, room["id"])

    resp = app_client.patch(
        f"/api/v1/sales/project-items/{item['id']}",
        headers=owner_headers,
        json={"production_status": "in_production", "installation_status": "scheduled"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["production_status"] == "in_production"
    assert body["installation_status"] == "scheduled"


def test_delete_project_item(app_client, owner_headers, customer):
    project = _create_project(app_client, owner_headers, customer.id)
    room = _create_room(app_client, owner_headers, project["id"])
    item = _create_item(app_client, owner_headers, room["id"])

    resp = app_client.delete(f"/api/v1/sales/project-items/{item['id']}", headers=owner_headers)
    assert resp.status_code == 204
    list_resp = app_client.get(f"/api/v1/sales/rooms/{room['id']}/items", headers=owner_headers)
    assert len(list_resp.json()["items"]) == 0


def test_project_item_audit_and_events(app_client, owner_headers, customer, db_session):
    project = _create_project(app_client, owner_headers, customer.id)
    room = _create_room(app_client, owner_headers, project["id"])
    _create_item(app_client, owner_headers, room["id"])

    assert "project_item.created" in _audit_actions(db_session, "project_item")
    assert "ProjectItemCreated" in _event_names(db_session)


# ── Measurements (with revisions) ─────────────────────────────────────────────


def test_create_measurement_computes_area(app_client, owner_headers, customer):
    project = _create_project(app_client, owner_headers, customer.id)
    room = _create_room(app_client, owner_headers, project["id"])
    item = _create_item(app_client, owner_headers, room["id"])

    resp = app_client.post(
        f"/api/v1/sales/project-items/{item['id']}/measurements",
        headers=owner_headers,
        json={
            "length_mm": "3000",
            "width_mm": "600",
            "quantity": 1,
            "measurer_name": "Ali Aliyev",
            "measured_at": "2026-07-01",
            "notes": "First site visit",
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert float(body["area_m2"]) == 1.8
    assert body["revision_number"] == 1
    assert body["measurer_name"] == "Ali Aliyev"


def test_second_measurement_is_a_new_revision(app_client, owner_headers, customer):
    project = _create_project(app_client, owner_headers, customer.id)
    room = _create_room(app_client, owner_headers, project["id"])
    item = _create_item(app_client, owner_headers, room["id"])

    first = app_client.post(
        f"/api/v1/sales/project-items/{item['id']}/measurements",
        headers=owner_headers,
        json={"length_mm": "3000", "width_mm": "600", "measurer_name": "Ali"},
    ).json()
    second = app_client.post(
        f"/api/v1/sales/project-items/{item['id']}/measurements",
        headers=owner_headers,
        json={"length_mm": "3050", "width_mm": "610", "measurer_name": "Ali"},
    ).json()

    assert first["revision_number"] == 1
    assert second["revision_number"] == 2

    list_resp = app_client.get(f"/api/v1/sales/project-items/{item['id']}/measurements", headers=owner_headers)
    revisions = list_resp.json()["items"]
    assert len(revisions) == 2
    # newest revision first
    assert revisions[0]["revision_number"] == 2


def test_update_measurement_records_customer_signature(app_client, owner_headers, customer):
    project = _create_project(app_client, owner_headers, customer.id)
    room = _create_room(app_client, owner_headers, project["id"])
    item = _create_item(app_client, owner_headers, room["id"])
    measurement = app_client.post(
        f"/api/v1/sales/project-items/{item['id']}/measurements",
        headers=owner_headers,
        json={"length_mm": "3000", "width_mm": "600"},
    ).json()

    upload = app_client.post(
        "/api/v1/core/documents",
        headers=owner_headers,
        data={"module": "sales", "related_entity_type": "project_item_measurement", "related_entity_id": measurement["id"]},
        files={"file": ("signature.png", io.BytesIO(b"fake-png-bytes"), "image/png")},
    )
    assert upload.status_code == 200, upload.text
    document_id = upload.json()["id"]

    resp = app_client.patch(
        f"/api/v1/sales/project-item-measurements/{measurement['id']}",
        headers=owner_headers,
        json={"status": "final", "customer_signature_document_id": document_id},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "final"
    assert body["customer_signature_document_id"] == document_id


def test_delete_measurement(app_client, owner_headers, customer):
    project = _create_project(app_client, owner_headers, customer.id)
    room = _create_room(app_client, owner_headers, project["id"])
    item = _create_item(app_client, owner_headers, room["id"])
    measurement = app_client.post(
        f"/api/v1/sales/project-items/{item['id']}/measurements",
        headers=owner_headers,
        json={"length_mm": "1000", "width_mm": "500"},
    ).json()

    resp = app_client.delete(
        f"/api/v1/sales/project-item-measurements/{measurement['id']}", headers=owner_headers
    )
    assert resp.status_code == 204
    list_resp = app_client.get(f"/api/v1/sales/project-items/{item['id']}/measurements", headers=owner_headers)
    assert len(list_resp.json()["items"]) == 0


def test_measurement_audit_and_events(app_client, owner_headers, customer, db_session):
    project = _create_project(app_client, owner_headers, customer.id)
    room = _create_room(app_client, owner_headers, project["id"])
    item = _create_item(app_client, owner_headers, room["id"])
    app_client.post(
        f"/api/v1/sales/project-items/{item['id']}/measurements",
        headers=owner_headers,
        json={"length_mm": "1000", "width_mm": "500"},
    )

    assert "project_item.measurement_recorded" in _audit_actions(db_session, "project_item_measurement")
    assert "ProjectItemMeasurementRecorded" in _event_names(db_session)


# ── Drawings & Photos ──────────────────────────────────────────────────────────


def test_add_and_list_drawing(app_client, owner_headers, customer):
    project = _create_project(app_client, owner_headers, customer.id)
    room = _create_room(app_client, owner_headers, project["id"])
    item = _create_item(app_client, owner_headers, room["id"])

    upload = app_client.post(
        "/api/v1/core/documents",
        headers=owner_headers,
        data={"module": "sales", "related_entity_type": "project_item_drawing", "related_entity_id": item["id"]},
        files={"file": ("plan.dwg", io.BytesIO(b"fake-dwg-bytes"), "application/octet-stream")},
    )
    assert upload.status_code == 200, upload.text
    document_id = upload.json()["id"]

    resp = app_client.post(
        f"/api/v1/sales/project-items/{item['id']}/drawings",
        headers=owner_headers,
        json={"document_id": document_id, "drawing_type": "dwg", "label": "Countertop plan"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["drawing_type"] == "dwg"

    list_resp = app_client.get(f"/api/v1/sales/project-items/{item['id']}/drawings", headers=owner_headers)
    assert len(list_resp.json()["items"]) == 1


def test_dxf_octet_stream_upload_allowed_by_extension(app_client, owner_headers, customer):
    project = _create_project(app_client, owner_headers, customer.id)
    room = _create_room(app_client, owner_headers, project["id"])
    item = _create_item(app_client, owner_headers, room["id"])

    upload = app_client.post(
        "/api/v1/core/documents",
        headers=owner_headers,
        data={"module": "sales", "related_entity_type": "project_item_drawing", "related_entity_id": item["id"]},
        files={"file": ("plan.dxf", io.BytesIO(b"fake-dxf-bytes"), "application/octet-stream")},
    )
    assert upload.status_code == 200, upload.text


def test_unsupported_octet_stream_extension_rejected(app_client, owner_headers, customer):
    project = _create_project(app_client, owner_headers, customer.id)
    room = _create_room(app_client, owner_headers, project["id"])
    item = _create_item(app_client, owner_headers, room["id"])

    upload = app_client.post(
        "/api/v1/core/documents",
        headers=owner_headers,
        data={"module": "sales", "related_entity_type": "project_item_drawing", "related_entity_id": item["id"]},
        files={"file": ("payload.exe", io.BytesIO(b"fake-exe-bytes"), "application/octet-stream")},
    )
    assert upload.status_code == 400


def test_delete_drawing(app_client, owner_headers, customer):
    project = _create_project(app_client, owner_headers, customer.id)
    room = _create_room(app_client, owner_headers, project["id"])
    item = _create_item(app_client, owner_headers, room["id"])
    upload = app_client.post(
        "/api/v1/core/documents",
        headers=owner_headers,
        data={"module": "sales", "related_entity_type": "project_item_drawing", "related_entity_id": item["id"]},
        files={"file": ("sketch.jpg", io.BytesIO(b"fake"), "image/jpeg")},
    ).json()
    drawing = app_client.post(
        f"/api/v1/sales/project-items/{item['id']}/drawings",
        headers=owner_headers,
        json={"document_id": upload["id"], "drawing_type": "sketch"},
    ).json()

    resp = app_client.delete(f"/api/v1/sales/project-item-drawings/{drawing['id']}", headers=owner_headers)
    assert resp.status_code == 204
    list_resp = app_client.get(f"/api/v1/sales/project-items/{item['id']}/drawings", headers=owner_headers)
    assert len(list_resp.json()["items"]) == 0


def test_add_and_delete_photo(app_client, owner_headers, customer):
    project = _create_project(app_client, owner_headers, customer.id)
    room = _create_room(app_client, owner_headers, project["id"])
    item = _create_item(app_client, owner_headers, room["id"])

    upload = app_client.post(
        "/api/v1/core/documents",
        headers=owner_headers,
        data={"module": "sales", "related_entity_type": "project_item_photo", "related_entity_id": item["id"]},
        files={"file": ("site.jpg", io.BytesIO(b"fake-jpg-bytes"), "image/jpeg")},
    ).json()

    resp = app_client.post(
        f"/api/v1/sales/project-items/{item['id']}/photos",
        headers=owner_headers,
        json={"document_id": upload["id"], "caption": "Before installation"},
    )
    assert resp.status_code == 200, resp.text
    photo = resp.json()
    assert photo["caption"] == "Before installation"

    list_resp = app_client.get(f"/api/v1/sales/project-items/{item['id']}/photos", headers=owner_headers)
    assert len(list_resp.json()["items"]) == 1

    del_resp = app_client.delete(f"/api/v1/sales/project-item-photos/{photo['id']}", headers=owner_headers)
    assert del_resp.status_code == 204
    list_resp2 = app_client.get(f"/api/v1/sales/project-items/{item['id']}/photos", headers=owner_headers)
    assert len(list_resp2.json()["items"]) == 0


# ── Tenant isolation ───────────────────────────────────────────────────────────


def test_rooms_are_isolated_by_company(app_client, owner_headers, customer, db_session):
    project = _create_project(app_client, owner_headers, customer.id)
    room = _create_room(app_client, owner_headers, project["id"])

    other_company = Company(name="KORONA PREMIUM", slug="korona-premium-rooms-test", enabled_modules=["sales"])
    db_session.add(other_company)
    db_session.flush()
    other_user = User(email="other-owner@rooms.test", password_hash=hash_password("x"), full_name="Other Owner")
    db_session.add(other_user)
    db_session.flush()
    db_session.add(UserCompanyRole(user_id=other_user.id, company_id=other_company.id, role=ROLE_OWNER))
    db_session.commit()
    other_token = create_access_token(user_id=other_user.id, active_company_id=other_company.id, role=ROLE_OWNER)
    other_headers = {"Authorization": f"Bearer {other_token}"}

    list_resp = app_client.get(f"/api/v1/sales/projects/{project['id']}/rooms", headers=other_headers)
    # Cross-tenant project_id lookup returns an empty list, never another company's rooms.
    assert list_resp.json()["items"] == []

    patch_resp = app_client.patch(f"/api/v1/sales/rooms/{room['id']}", headers=other_headers, json={"name": "Hijacked"})
    assert patch_resp.status_code == 404


# ── Sprint 5: expanded vocabulary + completion_status ("Təhvil") ──────────────


def test_new_sprint5_room_types_accepted(app_client, owner_headers, customer):
    project = _create_project(app_client, owner_headers, customer.id)
    for room_type in ["corridor", "balcony", "facade", "yard"]:
        resp = app_client.post(
            f"/api/v1/sales/projects/{project['id']}/rooms",
            headers=owner_headers,
            json={"room_type": room_type},
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["room_type"] == room_type


def test_legacy_room_types_still_accepted(app_client, owner_headers, customer):
    """staircase/exterior are no longer offered in the picker (PROJECT_ROOM_TYPES)
    but must remain valid so Rooms saved before Sprint 5 keep working."""
    project = _create_project(app_client, owner_headers, customer.id)
    for room_type in ["staircase", "exterior"]:
        resp = app_client.post(
            f"/api/v1/sales/projects/{project['id']}/rooms",
            headers=owner_headers,
            json={"room_type": room_type},
        )
        assert resp.status_code == 200, resp.text


def test_new_sprint5_item_types_accepted(app_client, owner_headers, customer):
    project = _create_project(app_client, owner_headers, customer.id)
    room = _create_room(app_client, owner_headers, project["id"])
    for item_type in ["fireplace", "window_sill"]:
        resp = app_client.post(
            f"/api/v1/sales/rooms/{room['id']}/items",
            headers=owner_headers,
            json={"item_type": item_type, "quantity": "1"},
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["item_type"] == item_type


def test_legacy_item_type_sink_still_accepted(app_client, owner_headers, customer):
    """sink is no longer in the curated PROJECT_ITEM_TYPES picker list but
    must remain valid so Items saved before Sprint 5 keep working."""
    project = _create_project(app_client, owner_headers, customer.id)
    room = _create_room(app_client, owner_headers, project["id"])
    resp = app_client.post(
        f"/api/v1/sales/rooms/{room['id']}/items",
        headers=owner_headers,
        json={"item_type": "sink", "quantity": "1"},
    )
    assert resp.status_code == 200, resp.text


def test_update_project_item_completion_status(app_client, owner_headers, customer):
    project = _create_project(app_client, owner_headers, customer.id)
    room = _create_room(app_client, owner_headers, project["id"])
    item = _create_item(app_client, owner_headers, room["id"])

    resp = app_client.patch(
        f"/api/v1/sales/project-items/{item['id']}",
        headers=owner_headers,
        json={"completion_status": "delivered"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["completion_status"] == "delivered"

    resp2 = app_client.patch(
        f"/api/v1/sales/project-items/{item['id']}",
        headers=owner_headers,
        json={"completion_status": "accepted"},
    )
    assert resp2.status_code == 200
    assert resp2.json()["completion_status"] == "accepted"


def test_new_project_item_has_null_completion_status(app_client, owner_headers, customer):
    project = _create_project(app_client, owner_headers, customer.id)
    room = _create_room(app_client, owner_headers, project["id"])
    item = _create_item(app_client, owner_headers, room["id"])
    assert item["completion_status"] is None
