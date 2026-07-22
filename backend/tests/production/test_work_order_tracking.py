"""Tests for the Production Job tracking surface (Phase 1: Stone
Fabrication Workflow, requirements #3/#5/#6): priority, operator
assignment, configurable-stage progression, due date/notes, and the
production timeline."""
import uuid


def test_create_work_order_with_priority_and_due_date(app_client, owner_headers, approved_order):
    resp = app_client.post(
        "/api/v1/production",
        headers=owner_headers,
        json={"order_id": approved_order["id"], "priority": "urgent", "due_date": "2026-08-01"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["priority"] == "urgent"
    assert body["scheduled_completion_date"] == "2026-08-01"


def test_create_work_order_defaults_priority_to_normal(app_client, owner_headers, approved_order):
    resp = app_client.post("/api/v1/production", headers=owner_headers, json={"order_id": approved_order["id"]})
    assert resp.json()["priority"] == "normal"


def test_update_work_order_priority(app_client, owner_headers, approved_order):
    work_order = app_client.post(
        "/api/v1/production", headers=owner_headers, json={"order_id": approved_order["id"]}
    ).json()

    resp = app_client.post(
        f"/api/v1/production/{work_order['id']}/priority", headers=owner_headers, json={"priority": "high"}
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["priority"] == "high"


def test_update_work_order_priority_rejects_invalid_value(app_client, owner_headers, approved_order):
    work_order = app_client.post(
        "/api/v1/production", headers=owner_headers, json={"order_id": approved_order["id"]}
    ).json()

    # A priority string outside the enum is a request-validation failure
    # (schema-level, model_post_init) -- same convention as every other
    # invalid-enum-value case in this codebase (e.g. WorkOrderStatusUpdate),
    # mapped to 400 by core's RequestValidationError handler, not 422
    # (reserved for business-rule violations raised by use cases).
    resp = app_client.post(
        f"/api/v1/production/{work_order['id']}/priority", headers=owner_headers, json={"priority": "critical"}
    )
    assert resp.status_code == 400


def test_assign_operator_requires_company_member(app_client, owner_headers, approved_order):
    work_order = app_client.post(
        "/api/v1/production", headers=owner_headers, json={"order_id": approved_order["id"]}
    ).json()

    resp = app_client.post(
        f"/api/v1/production/{work_order['id']}/assign",
        headers=owner_headers,
        json={"operator_user_id": str(uuid.uuid4())},
    )
    assert resp.status_code == 422, resp.text


def test_assign_and_unassign_operator(app_client, owner_headers, approved_order, owner_user):
    work_order = app_client.post(
        "/api/v1/production", headers=owner_headers, json={"order_id": approved_order["id"]}
    ).json()

    assigned = app_client.post(
        f"/api/v1/production/{work_order['id']}/assign",
        headers=owner_headers,
        json={"operator_user_id": str(owner_user.id)},
    )
    assert assigned.status_code == 200, assigned.text
    assert assigned.json()["assigned_to"] == str(owner_user.id)

    unassigned = app_client.post(
        f"/api/v1/production/{work_order['id']}/assign", headers=owner_headers, json={"operator_user_id": None}
    )
    assert unassigned.status_code == 200
    assert unassigned.json()["assigned_to"] is None


def test_update_work_order_due_date_and_notes(app_client, owner_headers, approved_order):
    work_order = app_client.post(
        "/api/v1/production", headers=owner_headers, json={"order_id": approved_order["id"]}
    ).json()

    resp = app_client.patch(
        f"/api/v1/production/{work_order['id']}",
        headers=owner_headers,
        json={"due_date": "2026-09-15", "notes": "Rush job for showroom opening"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["scheduled_completion_date"] == "2026-09-15"
    assert resp.json()["notes"] == "Rush job for showroom opening"


def test_move_work_order_through_stages(app_client, owner_headers, approved_order):
    work_order = app_client.post(
        "/api/v1/production", headers=owner_headers, json={"order_id": approved_order["id"]}
    ).json()
    stages = app_client.get("/api/v1/production/stages", headers=owner_headers).json()["items"]
    cnc_stage = next(s for s in stages if s["name"] == "CNC")

    resp = app_client.post(
        f"/api/v1/production/{work_order['id']}/stage", headers=owner_headers, json={"stage_id": cnc_stage["id"]}
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["current_stage_id"] == cnc_stage["id"]

    # Stages can move backward too -- real fabrication shops send pieces
    # back for rework, so no forward-only transition graph is enforced.
    measuring_stage = next(s for s in stages if s["name"] == "Measuring")
    back = app_client.post(
        f"/api/v1/production/{work_order['id']}/stage",
        headers=owner_headers,
        json={"stage_id": measuring_stage["id"]},
    )
    assert back.status_code == 200
    assert back.json()["current_stage_id"] == measuring_stage["id"]


def test_move_to_unknown_stage_returns_422(app_client, owner_headers, approved_order):
    work_order = app_client.post(
        "/api/v1/production", headers=owner_headers, json={"order_id": approved_order["id"]}
    ).json()

    resp = app_client.post(
        f"/api/v1/production/{work_order['id']}/stage",
        headers=owner_headers,
        json={"stage_id": str(uuid.uuid4())},
    )
    assert resp.status_code == 422


def test_timeline_records_creation_priority_and_status_changes(app_client, owner_headers, approved_order):
    work_order = app_client.post(
        "/api/v1/production",
        headers=owner_headers,
        json={"order_id": approved_order["id"], "priority": "high"},
    ).json()

    app_client.post(f"/api/v1/production/{work_order['id']}/priority", headers=owner_headers, json={"priority": "urgent"})
    app_client.post(f"/api/v1/production/{work_order['id']}/status", headers=owner_headers, json={"status": "cutting"})

    resp = app_client.get(f"/api/v1/production/{work_order['id']}/timeline", headers=owner_headers)
    assert resp.status_code == 200, resp.text
    events = resp.json()["items"]
    event_types = [e["event_type"] for e in events]
    assert event_types == ["created", "priority_changed", "status_changed"]
    # Chronological order (timeline requirement): each event's created_at is
    # non-decreasing across the list.
    timestamps = [e["created_at"] for e in events]
    assert timestamps == sorted(timestamps)


def test_cancel_work_order_releases_reservation_and_records_timeline_notes(
    app_client, owner_headers, approved_order, slab, db_session
):
    work_order = app_client.post(
        "/api/v1/production", headers=owner_headers, json={"order_id": approved_order["id"]}
    ).json()

    resp = app_client.post(
        f"/api/v1/production/{work_order['id']}/status",
        headers=owner_headers,
        json={"status": "cancelled", "cancelled_reason": "Customer changed material"},
    )
    assert resp.status_code == 200, resp.text

    db_session.refresh(slab)
    assert slab.status == "available"

    reservations = app_client.get(
        "/api/v1/catalog/reservations", headers=owner_headers, params={"order_id": approved_order["id"]}
    ).json()["items"]
    assert reservations, "Orders should have adopted a reservation for the slab-linked item"
    assert all(r["status"] == "released" for r in reservations)

    timeline = app_client.get(f"/api/v1/production/{work_order['id']}/timeline", headers=owner_headers).json()["items"]
    cancelled_event = next(e for e in timeline if e["event_type"] == "status_changed" and e["to_value"] == "cancelled")
    assert cancelled_event["notes"] == "Customer changed material"


def test_production_job_detail_shows_customer_project_and_material(
    app_client, owner_headers, approved_order, customer, project
):
    work_order = app_client.post(
        "/api/v1/production", headers=owner_headers, json={"order_id": approved_order["id"], "priority": "high"}
    ).json()

    resp = app_client.get(f"/api/v1/production/{work_order['id']}/job", headers=owner_headers)
    assert resp.status_code == 200, resp.text
    job = resp.json()

    assert job["customer"]["id"] == str(customer.id)
    assert job["customer"]["name"] == customer.name
    assert job["project"]["id"] == str(project.id)
    assert job["project"]["name"] == project.name
    assert job["priority"] == "high"
    assert job["order"]["id"] == approved_order["id"]
    assert len(job["items"]) == 1
    assert job["items"][0]["material_name"] == "Calacatta Gold"
    assert job["items"][0]["slab_number"]


def test_completing_work_order_marks_reservation_consumed(
    app_client, owner_headers, approved_order, slab, db_session
):
    work_order = app_client.post(
        "/api/v1/production", headers=owner_headers, json={"order_id": approved_order["id"]}
    ).json()

    for status in ("cutting", "polishing", "quality_check", "completed"):
        app_client.post(
            f"/api/v1/production/{work_order['id']}/status", headers=owner_headers, json={"status": status}
        )

    db_session.refresh(slab)
    assert slab.status == "consumed"

    reservations = app_client.get(
        "/api/v1/catalog/reservations", headers=owner_headers, params={"order_id": approved_order["id"]}
    ).json()["items"]
    assert reservations
    assert all(r["status"] == "consumed" for r in reservations)
