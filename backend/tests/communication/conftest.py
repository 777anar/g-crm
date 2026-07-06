import httpx
import pytest

from core.auth.models import ROLE_MANAGER, ROLE_OWNER, ROLE_REP, ROLE_VIEWER, User, UserCompanyRole
from core.auth.security import create_access_token, hash_password
from core.companies.models import Company
from modules.crm.infrastructure.models.customer import Customer


@pytest.fixture()
def company(db_session):
    company = Company(
        name="G-STONE COMMUNICATION TEST",
        slug="g-stone-communication-test",
        enabled_modules=["crm", "sales", "orders", "communication"],
    )
    db_session.add(company)
    db_session.commit()
    return company


@pytest.fixture()
def owner_user(db_session, company):
    user = User(email="owner@comm.test", password_hash=hash_password("Password123!"), full_name="Owner User")
    db_session.add(user)
    db_session.flush()
    db_session.add(UserCompanyRole(user_id=user.id, company_id=company.id, role=ROLE_OWNER))
    db_session.commit()
    return user


@pytest.fixture()
def viewer_user(db_session, company):
    user = User(email="viewer@comm.test", password_hash=hash_password("Password123!"), full_name="Viewer User")
    db_session.add(user)
    db_session.flush()
    db_session.add(UserCompanyRole(user_id=user.id, company_id=company.id, role=ROLE_VIEWER))
    db_session.commit()
    return user


@pytest.fixture()
def rep_user(db_session, company):
    user = User(email="rep@comm.test", password_hash=hash_password("Password123!"), full_name="Rep User")
    db_session.add(user)
    db_session.flush()
    db_session.add(UserCompanyRole(user_id=user.id, company_id=company.id, role=ROLE_REP))
    db_session.commit()
    return user


@pytest.fixture()
def manager_user(db_session, company):
    user = User(email="manager@comm.test", password_hash=hash_password("Password123!"), full_name="Manager User")
    db_session.add(user)
    db_session.flush()
    db_session.add(UserCompanyRole(user_id=user.id, company_id=company.id, role=ROLE_MANAGER))
    db_session.commit()
    return user


def _auth_headers(user, company, role):
    token = create_access_token(user_id=user.id, active_company_id=company.id, role=role)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def owner_headers(owner_user, company):
    return _auth_headers(owner_user, company, ROLE_OWNER)


@pytest.fixture()
def viewer_headers(viewer_user, company):
    return _auth_headers(viewer_user, company, ROLE_VIEWER)


@pytest.fixture()
def rep_headers(rep_user, company):
    return _auth_headers(rep_user, company, ROLE_REP)


@pytest.fixture()
def manager_headers(manager_user, company):
    return _auth_headers(manager_user, company, ROLE_MANAGER)


@pytest.fixture()
def known_customer(db_session, company):
    customer = Customer(
        company_id=company.id,
        name="Rashad Aliyev",
        status="approved",
        type="individual",
        whatsapp="+994501234567",
        email="rashad@example.com",
    )
    db_session.add(customer)
    db_session.commit()
    return customer


@pytest.fixture()
def whatsapp_channel(app_client, owner_headers):
    resp = app_client.post(
        "/api/v1/communication/channels",
        headers=owner_headers,
        json={"channel_type": "whatsapp", "display_name": "Sales WhatsApp", "identifier": "+994501111111"},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


@pytest.fixture()
def webhook_channel(app_client, owner_headers):
    resp = app_client.post(
        "/api/v1/communication/channels",
        headers=owner_headers,
        json={"channel_type": "webhook", "display_name": "Partner Webhook"},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


@pytest.fixture()
def email_channel(app_client, owner_headers):
    resp = app_client.post(
        "/api/v1/communication/channels",
        headers=owner_headers,
        json={"channel_type": "email", "display_name": "Support Inbox", "identifier": "support@example.com"},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


@pytest.fixture()
def sms_channel(app_client, owner_headers):
    resp = app_client.post(
        "/api/v1/communication/channels",
        headers=owner_headers,
        json={"channel_type": "sms", "display_name": "Sales SMS", "identifier": "+994509998877"},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


@pytest.fixture()
def mock_httpx_responses(monkeypatch):
    """Queues canned httpx.Response objects, popped in call order, for every
    real provider that goes through `with httpx.Client(...) as client:
    client.get/post/request(...)`. httpx.Client.get/post are thin wrappers
    around Client.request, so patching `request` intercepts all of them --
    no real network call is ever made in this test suite.

    Starlette's own TestClient (`app_client`) is itself an httpx.Client
    subclass, so this only intercepts calls to a real-looking external host
    (graph.facebook.com, api.twilio.com, ...) and passes everything else
    (including the TestClient's in-process calls into our own FastAPI app)
    through to the original, unpatched method."""
    queue: list = []
    original_request = httpx.Client.request

    def fake_request(self, method, url, **kwargs):
        host = httpx.URL(url).host
        if host in ("testserver", "127.0.0.1", "localhost"):
            return original_request(self, method, url, **kwargs)
        if not queue:
            raise AssertionError("mock_httpx_responses queue is empty -- test made an unexpected HTTP call")
        item = queue.pop(0)
        if isinstance(item, Exception):
            raise item
        status_code, json_body = item
        request = httpx.Request(method, url)
        return httpx.Response(status_code, json=json_body, request=request)

    monkeypatch.setattr(httpx.Client, "request", fake_request)
    return queue


def configure_credential(app_client, headers, channel_id, *, provider, config, webhook_secret=None):
    body = {"provider": provider, "config": config}
    if webhook_secret:
        body["webhook_secret"] = webhook_secret
    resp = app_client.put(f"/api/v1/communication/channels/{channel_id}/credential", headers=headers, json=body)
    assert resp.status_code == 200, resp.text
    return resp.json()
