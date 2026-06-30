"""Covers RELEASE_CHECKLIST.md H4: list endpoints must not silently hide
records past the page limit -- next_cursor must reflect reality."""


def test_customers_next_cursor_is_null_when_all_rows_fit_on_one_page(app_client, owner_headers):
    app_client.post("/api/v1/crm/customers", headers=owner_headers, json={"name": "Only Co", "type": "business"})

    response = app_client.get("/api/v1/crm/customers", headers=owner_headers, params={"limit": 25})
    assert response.status_code == 200
    assert response.json()["next_cursor"] is None


def test_customers_next_cursor_is_set_when_more_rows_exist(app_client, owner_headers):
    for i in range(3):
        app_client.post(
            "/api/v1/crm/customers", headers=owner_headers, json={"name": f"Co {i}", "type": "business"}
        )

    response = app_client.get("/api/v1/crm/customers", headers=owner_headers, params={"limit": 2})
    assert response.status_code == 200
    body = response.json()
    assert len(body["items"]) == 2
    assert body["next_cursor"] is not None


def test_customers_cursor_reaches_the_next_page(app_client, owner_headers):
    names = [f"Page Co {i}" for i in range(3)]
    for name in names:
        app_client.post("/api/v1/crm/customers", headers=owner_headers, json={"name": name, "type": "business"})

    first_page = app_client.get("/api/v1/crm/customers", headers=owner_headers, params={"limit": 2}).json()
    assert len(first_page["items"]) == 2
    assert first_page["next_cursor"] is not None

    second_page = app_client.get(
        "/api/v1/crm/customers", headers=owner_headers, params={"limit": 2, "cursor": first_page["next_cursor"]}
    ).json()
    assert len(second_page["items"]) == 1
    assert second_page["next_cursor"] is None

    first_ids = {c["id"] for c in first_page["items"]}
    second_ids = {c["id"] for c in second_page["items"]}
    assert first_ids.isdisjoint(second_ids)


def test_leads_next_cursor_reflects_more_rows(app_client, owner_headers):
    for i in range(3):
        app_client.post(
            "/api/v1/crm/leads",
            headers=owner_headers,
            json={"full_name": f"Lead {i}", "source_channel": "website"},
        )

    response = app_client.get("/api/v1/crm/leads", headers=owner_headers, params={"limit": 2})
    body = response.json()
    assert len(body["items"]) == 2
    assert body["next_cursor"] is not None

    next_page = app_client.get(
        "/api/v1/crm/leads", headers=owner_headers, params={"limit": 2, "cursor": body["next_cursor"]}
    ).json()
    assert len(next_page["items"]) == 1
    assert next_page["next_cursor"] is None


def test_malformed_cursor_fails_open_to_first_page(app_client, owner_headers):
    app_client.post("/api/v1/crm/customers", headers=owner_headers, json={"name": "Safe Co", "type": "business"})

    response = app_client.get(
        "/api/v1/crm/customers", headers=owner_headers, params={"cursor": "not-a-valid-cursor!!"}
    )
    assert response.status_code == 200
    assert len(response.json()["items"]) == 1
