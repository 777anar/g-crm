import uuid


def test_create_project(app_client, owner_headers, customer):
    resp = app_client.post(
        "/api/v1/sales/projects",
        headers=owner_headers,
        json={
            "customer_id": str(customer.id),
            "name": "Kitchen Renovation",
            "project_type": "kitchen",
            "address": "123 Main St",
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["name"] == "Kitchen Renovation"
    assert body["project_type"] == "kitchen"
    assert body["status"] == "active"


def test_list_projects(app_client, owner_headers, customer):
    app_client.post(
        "/api/v1/sales/projects",
        headers=owner_headers,
        json={"customer_id": str(customer.id), "name": "Project A"},
    )
    app_client.post(
        "/api/v1/sales/projects",
        headers=owner_headers,
        json={"customer_id": str(customer.id), "name": "Project B"},
    )
    resp = app_client.get("/api/v1/sales/projects", headers=owner_headers)
    assert resp.status_code == 200
    assert len(resp.json()["items"]) == 2


def test_get_project_not_found(app_client, owner_headers):
    resp = app_client.get(f"/api/v1/sales/projects/{uuid.uuid4()}", headers=owner_headers)
    assert resp.status_code == 404


def test_update_project(app_client, owner_headers, customer):
    proj = app_client.post(
        "/api/v1/sales/projects",
        headers=owner_headers,
        json={"customer_id": str(customer.id), "name": "Old Name"},
    ).json()
    resp = app_client.patch(
        f"/api/v1/sales/projects/{proj['id']}",
        headers=owner_headers,
        json={"name": "New Name"},
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "New Name"


def test_viewer_cannot_write_projects(app_client, viewer_headers, customer):
    resp = app_client.post(
        "/api/v1/sales/projects",
        headers=viewer_headers,
        json={"customer_id": str(customer.id), "name": "Should Fail"},
    )
    assert resp.status_code == 403


def test_filter_projects_by_customer(app_client, owner_headers, customer, db_session, company):
    from modules.crm.infrastructure.models.customer import Customer as CRMCustomer

    other = CRMCustomer(company_id=company.id, name="Other", status="active", type="individual")
    db_session.add(other)
    db_session.commit()

    app_client.post(
        "/api/v1/sales/projects",
        headers=owner_headers,
        json={"customer_id": str(customer.id), "name": "Mine"},
    )
    app_client.post(
        "/api/v1/sales/projects",
        headers=owner_headers,
        json={"customer_id": str(other.id), "name": "Other's"},
    )
    resp = app_client.get(
        f"/api/v1/sales/projects?customer_id={customer.id}", headers=owner_headers
    )
    assert resp.status_code == 200
    assert len(resp.json()["items"]) == 1
    assert resp.json()["items"][0]["name"] == "Mine"
