"""Tests for the Marketing module's Campaign CRUD and lifecycle."""


def test_create_and_get_campaign(app_client, owner_headers):
    resp = app_client.post(
        "/api/v1/marketing/campaigns",
        headers=owner_headers,
        json={"name": "Facebook Spring Sale", "channel": "facebook", "budget": "300.00"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["name"] == "Facebook Spring Sale"
    assert body["status"] == "draft"
    assert body["budget"] == "300.00"

    get_resp = app_client.get(f"/api/v1/marketing/campaigns/{body['id']}", headers=owner_headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["channel"] == "facebook"


def test_create_campaign_requires_write_permission(app_client, viewer_headers):
    resp = app_client.post(
        "/api/v1/marketing/campaigns", headers=viewer_headers, json={"name": "X", "channel": "instagram"}
    )
    assert resp.status_code == 403


def test_invalid_channel_rejected(app_client, owner_headers):
    resp = app_client.post(
        "/api/v1/marketing/campaigns", headers=owner_headers, json={"name": "X", "channel": "carrier_pigeon"}
    )
    assert resp.status_code == 400, resp.text


def test_campaign_search_and_filter(app_client, owner_headers):
    app_client.post("/api/v1/marketing/campaigns", headers=owner_headers, json={"name": "Instagram Push", "channel": "instagram"})
    app_client.post("/api/v1/marketing/campaigns", headers=owner_headers, json={"name": "Referral Bonus", "channel": "referral"})

    resp = app_client.get("/api/v1/marketing/campaigns", headers=owner_headers, params={"channel": "referral"})
    items = resp.json()["items"]
    assert len(items) == 1
    assert items[0]["name"] == "Referral Bonus"

    search_resp = app_client.get("/api/v1/marketing/campaigns", headers=owner_headers, params={"search": "push"})
    assert len(search_resp.json()["items"]) == 1


def test_campaign_status_transitions(app_client, owner_headers, campaign):
    # draft -> completed directly is illegal
    illegal = app_client.post(
        f"/api/v1/marketing/campaigns/{campaign['id']}/status", headers=owner_headers, json={"status": "completed"}
    )
    assert illegal.status_code == 422, illegal.text

    active = app_client.post(
        f"/api/v1/marketing/campaigns/{campaign['id']}/status", headers=owner_headers, json={"status": "active"}
    )
    assert active.status_code == 200
    assert active.json()["status"] == "active"

    completed = app_client.post(
        f"/api/v1/marketing/campaigns/{campaign['id']}/status", headers=owner_headers, json={"status": "completed"}
    )
    assert completed.status_code == 200
    assert completed.json()["status"] == "completed"

    # completed is terminal
    dead = app_client.post(
        f"/api/v1/marketing/campaigns/{campaign['id']}/status", headers=owner_headers, json={"status": "active"}
    )
    assert dead.status_code == 422, dead.text


def test_update_campaign_only_before_terminal_status(app_client, owner_headers, campaign):
    ok = app_client.patch(
        f"/api/v1/marketing/campaigns/{campaign['id']}", headers=owner_headers, json={"notes": "targeting 25-45yo"}
    )
    assert ok.status_code == 200
    assert ok.json()["notes"] == "targeting 25-45yo"

    app_client.post(f"/api/v1/marketing/campaigns/{campaign['id']}/status", headers=owner_headers, json={"status": "active"})
    app_client.post(f"/api/v1/marketing/campaigns/{campaign['id']}/status", headers=owner_headers, json={"status": "completed"})

    blocked = app_client.patch(
        f"/api/v1/marketing/campaigns/{campaign['id']}", headers=owner_headers, json={"notes": "too late"}
    )
    assert blocked.status_code == 422, blocked.text


def test_get_campaign_not_found(app_client, owner_headers):
    import uuid

    resp = app_client.get(f"/api/v1/marketing/campaigns/{uuid.uuid4()}", headers=owner_headers)
    assert resp.status_code == 404


def test_campaigns_cursor_reaches_the_next_page(app_client, owner_headers):
    ids = []
    for name in ["Campaign A", "Campaign B", "Campaign C"]:
        resp = app_client.post(
            "/api/v1/marketing/campaigns", headers=owner_headers, json={"name": name, "channel": "other"}
        )
        ids.append(resp.json()["id"])

    first_page = app_client.get("/api/v1/marketing/campaigns", headers=owner_headers, params={"limit": 2}).json()
    assert len(first_page["items"]) == 2
    assert first_page["next_cursor"] is not None

    second_page = app_client.get(
        "/api/v1/marketing/campaigns", headers=owner_headers, params={"limit": 2, "cursor": first_page["next_cursor"]}
    ).json()
    assert len(second_page["items"]) == 1
    assert second_page["next_cursor"] is None

    first_ids = {c["id"] for c in first_page["items"]}
    second_ids = {c["id"] for c in second_page["items"]}
    assert first_ids.isdisjoint(second_ids)
    assert first_ids | second_ids == set(ids)
