import uuid


def _create_project(client, headers, customer_id, name="Kitchen Renovation"):
    return client.post(
        "/api/v1/sales/projects",
        headers=headers,
        json={"customer_id": str(customer_id), "name": name},
    ).json()


def test_create_quote(app_client, owner_headers, customer):
    proj = _create_project(app_client, owner_headers, customer.id)
    resp = app_client.post(
        f"/api/v1/sales/projects/{proj['id']}/quotes",
        headers=owner_headers,
        json={"currency": "AZN", "vat_rate": "18"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "draft"
    assert body["currency"] == "AZN"
    assert body["quote_number"].startswith("QT-")
    assert "-v1" in body["quote_number"]


def test_quote_number_increments(app_client, owner_headers, customer):
    proj = _create_project(app_client, owner_headers, customer.id)
    q1 = app_client.post(
        f"/api/v1/sales/projects/{proj['id']}/quotes",
        headers=owner_headers,
        json={},
    ).json()
    q2 = app_client.post(
        f"/api/v1/sales/projects/{proj['id']}/quotes",
        headers=owner_headers,
        json={},
    ).json()
    assert q1["quote_number"] != q2["quote_number"]


def test_update_draft_quote(app_client, owner_headers, customer):
    proj = _create_project(app_client, owner_headers, customer.id)
    quote = app_client.post(
        f"/api/v1/sales/projects/{proj['id']}/quotes",
        headers=owner_headers,
        json={},
    ).json()
    resp = app_client.patch(
        f"/api/v1/sales/quotes/{quote['id']}",
        headers=owner_headers,
        json={"customer_notes": "Updated notes"},
    )
    assert resp.status_code == 200
    assert resp.json()["customer_notes"] == "Updated notes"
    assert resp.json()["status"] == "draft"


def test_status_transition_draft_to_sent(app_client, owner_headers, customer):
    proj = _create_project(app_client, owner_headers, customer.id)
    quote = app_client.post(
        f"/api/v1/sales/projects/{proj['id']}/quotes",
        headers=owner_headers,
        json={},
    ).json()
    resp = app_client.post(
        f"/api/v1/sales/quotes/{quote['id']}/status",
        headers=owner_headers,
        json={"status": "sent"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "sent"


def test_invalid_status_transition_rejected(app_client, owner_headers, customer):
    proj = _create_project(app_client, owner_headers, customer.id)
    quote = app_client.post(
        f"/api/v1/sales/projects/{proj['id']}/quotes",
        headers=owner_headers,
        json={},
    ).json()
    resp = app_client.post(
        f"/api/v1/sales/quotes/{quote['id']}/status",
        headers=owner_headers,
        json={"status": "accepted"},
    )
    assert resp.status_code == 422


def test_edit_immutable_quote_forks_new_version(app_client, owner_headers, customer):
    proj = _create_project(app_client, owner_headers, customer.id)
    quote = app_client.post(
        f"/api/v1/sales/projects/{proj['id']}/quotes",
        headers=owner_headers,
        json={},
    ).json()
    app_client.post(
        f"/api/v1/sales/quotes/{quote['id']}/status",
        headers=owner_headers,
        json={"status": "sent"},
    )
    # Edit a sent quote → should return a new v2 draft
    forked = app_client.patch(
        f"/api/v1/sales/quotes/{quote['id']}",
        headers=owner_headers,
        json={"customer_notes": "Changed after sent"},
    ).json()
    assert forked["version"] == 2
    assert forked["status"] == "draft"
    assert "-v2" in forked["quote_number"]


def test_list_quotes_for_project(app_client, owner_headers, customer):
    proj = _create_project(app_client, owner_headers, customer.id)
    app_client.post(f"/api/v1/sales/projects/{proj['id']}/quotes", headers=owner_headers, json={})
    app_client.post(f"/api/v1/sales/projects/{proj['id']}/quotes", headers=owner_headers, json={})
    resp = app_client.get(f"/api/v1/sales/projects/{proj['id']}/quotes", headers=owner_headers)
    assert resp.status_code == 200
    assert len(resp.json()["items"]) == 2


def test_quote_not_found(app_client, owner_headers):
    resp = app_client.get(f"/api/v1/sales/quotes/{uuid.uuid4()}", headers=owner_headers)
    assert resp.status_code == 404
