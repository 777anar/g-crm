"""Tests for e-signature integration (Phase 22) on installation job
completion sign-off: POST .../request-signature, .../simulate-signature
(mock only), and the public webhook -- an alternative to the existing
canvas SignaturePad capture, producing the same photo_type="signature"
InstallationPhoto row once completed."""
import json

import pytest

from core.auth.models import ROLE_VIEWER, User, UserCompanyRole
from core.auth.security import create_access_token, hash_password
from modules.crm.infrastructure.models.customer import Customer


@pytest.fixture()
def customer(db_session, company):
    # Overrides the shared installation conftest fixture (no email there) --
    # e-signature requires a signer email.
    c = Customer(
        company_id=company.id, name="Test Customer", status="approved", type="individual", email="customer@example.com",
    )
    db_session.add(c)
    db_session.commit()
    return c


@pytest.fixture()
def viewer_user(db_session, company):
    user = User(email="viewer@installation.test", password_hash=hash_password("Password123!"), full_name="Viewer User")
    db_session.add(user)
    db_session.flush()
    db_session.add(UserCompanyRole(user_id=user.id, company_id=company.id, role=ROLE_VIEWER))
    db_session.commit()
    return user


@pytest.fixture()
def viewer_headers(viewer_user, company):
    token = create_access_token(user_id=viewer_user.id, active_company_id=company.id, role=ROLE_VIEWER)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def installation_job(app_client, owner_headers, ready_order):
    resp = app_client.post("/api/v1/installation/jobs", headers=owner_headers, json={"order_id": ready_order["id"]})
    assert resp.status_code == 200, resp.text
    return resp.json()


def test_request_signature_uses_mock_provider_by_default(app_client, owner_headers, installation_job):
    resp = app_client.post(
        f"/api/v1/installation/jobs/{installation_job['id']}/request-signature", headers=owner_headers, json={}
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["signature_provider"] == "mock"
    assert body["signature_status"] == "sent"


def test_request_signature_requires_customer_email(app_client, owner_headers, db_session, ready_order):
    from modules.crm.infrastructure.models.customer import Customer

    resp = app_client.post("/api/v1/installation/jobs", headers=owner_headers, json={"order_id": ready_order["id"]})
    assert resp.status_code == 200, resp.text
    job = resp.json()

    # Clear the customer's email to simulate the gap -- request-signature
    # must fail before any provider call happens.
    customer_row = db_session.get(Customer, ready_order["customer_id"])
    customer_row.email = None
    db_session.commit()

    sig_resp = app_client.post(
        f"/api/v1/installation/jobs/{job['id']}/request-signature", headers=owner_headers, json={}
    )
    assert sig_resp.status_code == 400


def test_simulate_signature_completed_creates_signature_photo(app_client, owner_headers, installation_job):
    app_client.post(f"/api/v1/installation/jobs/{installation_job['id']}/request-signature", headers=owner_headers, json={})
    resp = app_client.post(
        f"/api/v1/installation/jobs/{installation_job['id']}/simulate-signature",
        headers=owner_headers,
        json={"outcome": "completed"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["signature_status"] == "completed"

    photos = app_client.get(f"/api/v1/installation/jobs/{installation_job['id']}/photos", headers=owner_headers).json()
    assert any(p["photo_type"] == "signature" for p in photos["items"])


def test_simulate_signature_declined_creates_no_photo(app_client, owner_headers, installation_job):
    app_client.post(f"/api/v1/installation/jobs/{installation_job['id']}/request-signature", headers=owner_headers, json={})
    resp = app_client.post(
        f"/api/v1/installation/jobs/{installation_job['id']}/simulate-signature",
        headers=owner_headers,
        json={"outcome": "declined"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["signature_status"] == "declined"

    photos = app_client.get(f"/api/v1/installation/jobs/{installation_job['id']}/photos", headers=owner_headers).json()
    assert not any(p["photo_type"] == "signature" for p in photos["items"])


def test_simulate_signature_rejected_without_a_pending_request(app_client, owner_headers, installation_job):
    resp = app_client.post(
        f"/api/v1/installation/jobs/{installation_job['id']}/simulate-signature",
        headers=owner_headers,
        json={"outcome": "completed"},
    )
    assert resp.status_code == 400


def test_webhook_completes_signature_and_is_idempotent(app_client, owner_headers, installation_job, db_session):
    from modules.installation.infrastructure.models.installation_job import InstallationJob

    app_client.post(f"/api/v1/installation/jobs/{installation_job['id']}/request-signature", headers=owner_headers, json={})
    row = db_session.get(InstallationJob, installation_job["id"])
    provider_request_id = row.signature_provider_request_id

    payload = json.dumps({"provider_request_id": provider_request_id, "status": "completed"})
    resp = app_client.post("/api/v1/installation/webhooks/esignature/mock", data={"json": payload})
    assert resp.status_code == 200, resp.text

    db_session.refresh(row)
    assert row.signature_status == "completed"

    resp2 = app_client.post("/api/v1/installation/webhooks/esignature/mock", data={"json": payload})
    assert resp2.status_code == 200, resp2.text


def test_webhook_unknown_request_id_is_a_no_op(app_client):
    payload = json.dumps({"provider_request_id": "mock-does-not-exist", "status": "completed"})
    resp = app_client.post("/api/v1/installation/webhooks/esignature/mock", data={"json": payload})
    assert resp.status_code == 200, resp.text


def test_request_signature_requires_write_permission(app_client, viewer_headers, installation_job):
    resp = app_client.post(
        f"/api/v1/installation/jobs/{installation_job['id']}/request-signature", headers=viewer_headers, json={}
    )
    assert resp.status_code == 403
