"""Tests for e-signature integration (Phase 22) on measurement sign-off:
POST .../request-signature, .../simulate-signature (mock only), and the
public webhook -- draft-only in the sense that nothing is emailed/signed for
real until a provider confirms it, and the manual customer_signature_document_id
upload path (Phase 9) keeps working unchanged alongside it."""
import json

import pytest

from modules.crm.infrastructure.models.customer import Customer


@pytest.fixture()
def customer(db_session, company):
    # Overrides the shared sales conftest fixture (no email there) --
    # e-signature requires a signer email.
    c = Customer(
        company_id=company.id, name="Test Customer", status="active", type="individual", email="customer@example.com",
    )
    db_session.add(c)
    db_session.commit()
    return c


def _create_project(client, headers, customer_id):
    return client.post(
        "/api/v1/sales/projects", headers=headers, json={"customer_id": str(customer_id), "name": "Renovation"}
    ).json()


def _create_room(client, headers, project_id):
    return client.post(
        f"/api/v1/sales/projects/{project_id}/rooms", headers=headers, json={"room_type": "kitchen", "name": "Kitchen"}
    ).json()


def _create_item(client, headers, room_id):
    return client.post(
        f"/api/v1/sales/rooms/{room_id}/items", headers=headers, json={"item_type": "countertop", "quantity": "1"}
    ).json()


def _create_measurement(client, headers, item_id):
    return client.post(
        f"/api/v1/sales/project-items/{item_id}/measurements",
        headers=headers,
        json={"length_mm": "3000", "width_mm": "600", "measurer_name": "Ali Aliyev", "measured_at": "2026-07-01"},
    ).json()


@pytest.fixture()
def measurement(app_client, owner_headers, customer):
    project = _create_project(app_client, owner_headers, customer.id)
    room = _create_room(app_client, owner_headers, project["id"])
    item = _create_item(app_client, owner_headers, room["id"])
    return _create_measurement(app_client, owner_headers, item["id"])


def test_request_signature_uses_mock_provider_by_default(app_client, owner_headers, measurement):
    resp = app_client.post(
        f"/api/v1/sales/project-item-measurements/{measurement['id']}/request-signature",
        headers=owner_headers,
        json={},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["signature_provider"] == "mock"
    assert body["signature_status"] == "sent"


def test_request_signature_requires_customer_email(app_client, owner_headers, db_session, company):
    c = Customer(company_id=company.id, name="No Email Customer", status="active", type="individual")
    db_session.add(c)
    db_session.commit()
    project = _create_project(app_client, owner_headers, c.id)
    room = _create_room(app_client, owner_headers, project["id"])
    item = _create_item(app_client, owner_headers, room["id"])
    m = _create_measurement(app_client, owner_headers, item["id"])

    resp = app_client.post(
        f"/api/v1/sales/project-item-measurements/{m['id']}/request-signature", headers=owner_headers, json={}
    )
    assert resp.status_code == 400


def test_simulate_signature_completed_sets_document_and_final_status(app_client, owner_headers, measurement):
    app_client.post(
        f"/api/v1/sales/project-item-measurements/{measurement['id']}/request-signature",
        headers=owner_headers,
        json={},
    )
    resp = app_client.post(
        f"/api/v1/sales/project-item-measurements/{measurement['id']}/simulate-signature",
        headers=owner_headers,
        json={"outcome": "completed"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["signature_status"] == "completed"
    assert body["status"] == "final"
    assert body["customer_signature_document_id"] is not None


def test_simulate_signature_declined_does_not_set_document(app_client, owner_headers, measurement):
    app_client.post(
        f"/api/v1/sales/project-item-measurements/{measurement['id']}/request-signature",
        headers=owner_headers,
        json={},
    )
    resp = app_client.post(
        f"/api/v1/sales/project-item-measurements/{measurement['id']}/simulate-signature",
        headers=owner_headers,
        json={"outcome": "declined"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["signature_status"] == "declined"
    assert body["customer_signature_document_id"] is None


def test_simulate_signature_rejected_without_a_pending_request(app_client, owner_headers, measurement):
    resp = app_client.post(
        f"/api/v1/sales/project-item-measurements/{measurement['id']}/simulate-signature",
        headers=owner_headers,
        json={"outcome": "completed"},
    )
    assert resp.status_code == 400


def test_webhook_completes_signature_and_is_idempotent(app_client, owner_headers, measurement, db_session):
    from modules.sales.infrastructure.models.project_item_measurement import ProjectItemMeasurement

    app_client.post(
        f"/api/v1/sales/project-item-measurements/{measurement['id']}/request-signature",
        headers=owner_headers,
        json={},
    )
    row = db_session.get(ProjectItemMeasurement, measurement["id"])
    provider_request_id = row.signature_provider_request_id

    payload = json.dumps({"provider_request_id": provider_request_id, "status": "completed"})
    resp = app_client.post(
        "/api/v1/sales/webhooks/esignature/mock", data={"json": payload}
    )
    assert resp.status_code == 200, resp.text

    db_session.refresh(row)
    assert row.signature_status == "completed"
    assert row.customer_signature_document_id is not None

    # Idempotent: a retried webhook delivery must not error or double-process.
    resp2 = app_client.post("/api/v1/sales/webhooks/esignature/mock", data={"json": payload})
    assert resp2.status_code == 200, resp2.text


def test_webhook_unknown_request_id_is_a_no_op(app_client):
    payload = json.dumps({"provider_request_id": "mock-does-not-exist", "status": "completed"})
    resp = app_client.post("/api/v1/sales/webhooks/esignature/mock", data={"json": payload})
    assert resp.status_code == 200, resp.text


def test_request_signature_requires_write_permission(app_client, viewer_headers, measurement):
    resp = app_client.post(
        f"/api/v1/sales/project-item-measurements/{measurement['id']}/request-signature",
        headers=viewer_headers,
        json={},
    )
    assert resp.status_code == 403
