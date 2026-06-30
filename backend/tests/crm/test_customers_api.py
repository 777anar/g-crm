def test_create_customer(app_client, owner_headers):
    response = app_client.post(
        "/api/v1/crm/customers",
        headers=owner_headers,
        json={
            "name": "Acme Renovations",
            "type": "business",
            "lead_source": "manual",
            "tags": ["vip"],
            "contact": {"full_name": "John Doe", "email": "john@acme.test", "phone": "+994501234567"},
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["name"] == "Acme Renovations"
    assert body["type"] == "business"
    assert body["primary_contact_id"] is not None
    assert body["deleted_at"] is None


def test_create_customer_requires_write_permission(app_client, viewer_headers):
    response = app_client.post(
        "/api/v1/crm/customers", headers=viewer_headers, json={"name": "No Access Co", "type": "business"}
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"


def test_create_customer_unauthenticated(app_client):
    response = app_client.post("/api/v1/crm/customers", json={"name": "X", "type": "business"})
    assert response.status_code == 401


def test_list_customers(app_client, owner_headers):
    app_client.post("/api/v1/crm/customers", headers=owner_headers, json={"name": "Customer A", "type": "business"})
    app_client.post("/api/v1/crm/customers", headers=owner_headers, json={"name": "Customer B", "type": "individual"})

    response = app_client.get("/api/v1/crm/customers", headers=owner_headers)
    assert response.status_code == 200
    body = response.json()
    names = {c["name"] for c in body["items"]}
    assert {"Customer A", "Customer B"}.issubset(names)


def test_get_customer(app_client, owner_headers):
    created = app_client.post(
        "/api/v1/crm/customers", headers=owner_headers, json={"name": "Lookup Co", "type": "business"}
    ).json()

    response = app_client.get(f"/api/v1/crm/customers/{created['id']}", headers=owner_headers)
    assert response.status_code == 200
    assert response.json()["name"] == "Lookup Co"


def test_get_customer_not_found(app_client, owner_headers):
    import uuid

    response = app_client.get(f"/api/v1/crm/customers/{uuid.uuid4()}", headers=owner_headers)
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"


def test_update_customer(app_client, owner_headers):
    created = app_client.post(
        "/api/v1/crm/customers", headers=owner_headers, json={"name": "Old Name", "type": "business"}
    ).json()

    response = app_client.patch(
        f"/api/v1/crm/customers/{created['id']}",
        headers=owner_headers,
        json={"name": "New Name", "advertising_campaign": "Spring Promo"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "New Name"
    assert body["advertising_campaign"] == "Spring Promo"


def test_archive_customer(app_client, owner_headers):
    created = app_client.post(
        "/api/v1/crm/customers", headers=owner_headers, json={"name": "To Archive", "type": "business"}
    ).json()

    response = app_client.delete(f"/api/v1/crm/customers/{created['id']}", headers=owner_headers)
    assert response.status_code == 200
    assert response.json()["deleted_at"] is not None

    listed = app_client.get("/api/v1/crm/customers", headers=owner_headers).json()
    assert created["id"] not in [c["id"] for c in listed["items"]]

    listed_with_archived = app_client.get(
        "/api/v1/crm/customers", headers=owner_headers, params={"include_archived": True}
    ).json()
    assert created["id"] in [c["id"] for c in listed_with_archived["items"]]


def test_archive_already_archived_customer_returns_conflict(app_client, owner_headers):
    created = app_client.post(
        "/api/v1/crm/customers", headers=owner_headers, json={"name": "Double Archive", "type": "business"}
    ).json()
    app_client.delete(f"/api/v1/crm/customers/{created['id']}", headers=owner_headers)

    response = app_client.delete(f"/api/v1/crm/customers/{created['id']}", headers=owner_headers)
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "CONFLICT"


def test_add_and_list_customer_notes(app_client, owner_headers):
    created = app_client.post(
        "/api/v1/crm/customers", headers=owner_headers, json={"name": "Notes Co", "type": "business"}
    ).json()

    note_response = app_client.post(
        f"/api/v1/crm/customers/{created['id']}/notes", headers=owner_headers, json={"body": "Called the client."}
    )
    assert note_response.status_code == 200
    assert note_response.json()["body"] == "Called the client."
    assert note_response.json()["type"] == "note"

    notes = app_client.get(f"/api/v1/crm/customers/{created['id']}/notes", headers=owner_headers).json()
    assert len(notes) == 1
    assert notes[0]["body"] == "Called the client."


def test_customer_profile_includes_all_required_sections(app_client, owner_headers):
    created = app_client.post(
        "/api/v1/crm/customers",
        headers=owner_headers,
        json={
            "name": "Profile Co",
            "type": "business",
            "lead_source": "instagram",
            "advertising_campaign": "Summer Sale",
            "contact": {"full_name": "Jane Doe", "email": "jane@profile.test"},
        },
    ).json()
    app_client.post(
        f"/api/v1/crm/customers/{created['id']}/notes", headers=owner_headers, json={"body": "First contact made."}
    )

    response = app_client.get(f"/api/v1/crm/customers/{created['id']}/profile", headers=owner_headers)
    assert response.status_code == 200
    profile = response.json()

    assert profile["customer"]["name"] == "Profile Co"
    assert profile["customer"]["lead_source"] == "instagram"
    assert profile["customer"]["advertising_campaign"] == "Summer Sale"
    assert len(profile["contacts"]) == 1
    assert profile["contacts"][0]["full_name"] == "Jane Doe"
    # System "customer created" entry + the note = 2 timeline entries.
    assert len(profile["timeline"]) == 2
    # Projects/Quotes/Orders/Payments: real, empty sections -- those modules
    # (Production/Sales/Finance) are not installed yet in this phase.
    assert profile["projects"] == []
    assert profile["quotes"] == []
    assert profile["orders"] == []
    assert profile["payments"] == []
    assert profile["attachments"] == []


def test_customer_attachment_upload_and_list(app_client, owner_headers):
    created = app_client.post(
        "/api/v1/crm/customers", headers=owner_headers, json={"name": "Attachment Co", "type": "business"}
    ).json()

    upload = app_client.post(
        "/api/v1/core/documents",
        headers=owner_headers,
        data={"module": "crm", "related_entity_type": "customer", "related_entity_id": created["id"]},
        files={"file": ("contract.pdf", b"%PDF-1.4 fake content", "application/pdf")},
    )
    assert upload.status_code == 200, upload.text

    attachments = app_client.get(
        f"/api/v1/crm/customers/{created['id']}/attachments", headers=owner_headers
    ).json()
    assert len(attachments) == 1
    assert attachments[0]["mime_type"] == "application/pdf"


def test_customers_are_isolated_by_company(app_client, db_session, owner_headers, company):
    from core.auth.models import ROLE_OWNER, User, UserCompanyRole
    from core.auth.security import create_access_token, hash_password
    from core.companies.models import Company

    other_company = Company(name="KORONA PREMIUM", slug="korona-premium-2", enabled_modules=["crm"])
    db_session.add(other_company)
    db_session.flush()
    other_user = User(email="other-owner@test.example", password_hash=hash_password("x"), full_name="Other Owner")
    db_session.add(other_user)
    db_session.flush()
    db_session.add(UserCompanyRole(user_id=other_user.id, company_id=other_company.id, role=ROLE_OWNER))
    db_session.commit()
    other_token = create_access_token(user_id=other_user.id, active_company_id=other_company.id, role=ROLE_OWNER)
    other_headers = {"Authorization": f"Bearer {other_token}"}

    created = app_client.post(
        "/api/v1/crm/customers", headers=owner_headers, json={"name": "Isolated Co", "type": "business"}
    ).json()

    response = app_client.get(f"/api/v1/crm/customers/{created['id']}", headers=other_headers)
    assert response.status_code == 404
