"""Tests for Installation crew management."""


def test_create_crew(app_client, owner_headers):
    resp = app_client.post("/api/v1/installation/crews", headers=owner_headers, json={"name": "Team Beta"})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["name"] == "Team Beta"
    assert body["status"] == "active"


def test_add_and_list_crew_members(app_client, owner_headers, crew, installer_user):
    resp = app_client.get(f"/api/v1/installation/crews/{crew['id']}/members", headers=owner_headers)
    assert resp.status_code == 200, resp.text
    members = resp.json()["items"]
    assert len(members) == 1
    assert members[0]["user_id"] == str(installer_user.id)
    assert members[0]["is_lead"] is True
    assert members[0]["full_name"] == "Ivan Installer"


def test_add_duplicate_member_returns_400(app_client, owner_headers, crew, installer_user):
    resp = app_client.post(
        f"/api/v1/installation/crews/{crew['id']}/members",
        headers=owner_headers,
        json={"user_id": str(installer_user.id)},
    )
    assert resp.status_code == 400, resp.text


def test_remove_crew_member(app_client, owner_headers, crew, installer_user):
    members = app_client.get(f"/api/v1/installation/crews/{crew['id']}/members", headers=owner_headers).json()["items"]
    member_id = members[0]["id"]

    resp = app_client.delete(
        f"/api/v1/installation/crews/{crew['id']}/members/{member_id}", headers=owner_headers
    )
    assert resp.status_code == 204, resp.text

    remaining = app_client.get(f"/api/v1/installation/crews/{crew['id']}/members", headers=owner_headers).json()["items"]
    assert remaining == []


def test_update_crew_status(app_client, owner_headers, crew):
    resp = app_client.patch(
        f"/api/v1/installation/crews/{crew['id']}", headers=owner_headers, json={"status": "inactive"}
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "inactive"


def test_list_crews_filters_by_status(app_client, owner_headers, crew):
    app_client.patch(f"/api/v1/installation/crews/{crew['id']}", headers=owner_headers, json={"status": "inactive"})
    resp = app_client.get("/api/v1/installation/crews", headers=owner_headers, params={"status": "active"})
    assert resp.status_code == 200
    assert all(c["id"] != crew["id"] for c in resp.json()["items"])
