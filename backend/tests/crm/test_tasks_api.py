"""Tests for the Tasks & Reminders feature's CRUD and status lifecycle."""


def test_create_task_minimal(app_client, owner_headers):
    resp = app_client.post("/api/v1/crm/tasks", headers=owner_headers, json={"title": "Call back customer"})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["title"] == "Call back customer"
    assert body["status"] == "pending"
    assert body["priority"] == "medium"
    assert body["tags"] == []
    assert body["assigned_to"] is None


def test_create_task_requires_write_permission(app_client, viewer_headers):
    resp = app_client.post("/api/v1/crm/tasks", headers=viewer_headers, json={"title": "No access"})
    assert resp.status_code == 403


def test_viewer_can_list_tasks(app_client, owner_headers, viewer_headers):
    app_client.post("/api/v1/crm/tasks", headers=owner_headers, json={"title": "Visible to viewer"})
    resp = app_client.get("/api/v1/crm/tasks", headers=viewer_headers)
    assert resp.status_code == 200
    assert len(resp.json()["items"]) == 1


def test_create_task_with_full_fields(app_client, owner_headers, rep_user):
    resp = app_client.post(
        "/api/v1/crm/tasks",
        headers=owner_headers,
        json={
            "title": "Follow up on quote",
            "description": "Call about QT-2026-0001",
            "priority": "high",
            "due_date": "2026-08-01T09:00:00Z",
            "assigned_to": str(rep_user.id),
            "tags": ["follow-up", "quote"],
            "related_entity_type": "customer",
            "related_entity_id": "11111111-1111-1111-1111-111111111111",
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["priority"] == "high"
    assert body["assigned_to"] == str(rep_user.id)
    assert body["tags"] == ["follow-up", "quote"]
    assert body["related_entity_type"] == "customer"


def test_create_task_with_unknown_assignee_returns_400(app_client, owner_headers):
    import uuid

    resp = app_client.post(
        "/api/v1/crm/tasks",
        headers=owner_headers,
        json={"title": "Bad assignee", "assigned_to": str(uuid.uuid4())},
    )
    assert resp.status_code == 400, resp.text


def test_create_task_invalid_priority_returns_400(app_client, owner_headers):
    resp = app_client.post(
        "/api/v1/crm/tasks", headers=owner_headers, json={"title": "Bad priority", "priority": "urgentest"}
    )
    assert resp.status_code == 400, resp.text


def test_get_and_update_task(app_client, owner_headers):
    task = app_client.post("/api/v1/crm/tasks", headers=owner_headers, json={"title": "Original"}).json()

    resp = app_client.patch(
        f"/api/v1/crm/tasks/{task['id']}", headers=owner_headers, json={"title": "Updated", "priority": "urgent"}
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["title"] == "Updated"
    assert body["priority"] == "urgent"

    fetched = app_client.get(f"/api/v1/crm/tasks/{task['id']}", headers=owner_headers)
    assert fetched.json()["title"] == "Updated"


def test_update_task_requires_write_permission(app_client, owner_headers, viewer_headers):
    task = app_client.post("/api/v1/crm/tasks", headers=owner_headers, json={"title": "Locked"}).json()
    resp = app_client.patch(f"/api/v1/crm/tasks/{task['id']}", headers=viewer_headers, json={"title": "Hacked"})
    assert resp.status_code == 403


def test_status_transition_pending_to_in_progress_to_done(app_client, owner_headers):
    task = app_client.post("/api/v1/crm/tasks", headers=owner_headers, json={"title": "Progress me"}).json()

    resp = app_client.post(
        f"/api/v1/crm/tasks/{task['id']}/status", headers=owner_headers, json={"status": "in_progress"}
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "in_progress"

    resp = app_client.post(f"/api/v1/crm/tasks/{task['id']}/status", headers=owner_headers, json={"status": "done"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "done"
    assert body["completed_at"] is not None


def test_cannot_transition_from_terminal_status(app_client, owner_headers):
    task = app_client.post("/api/v1/crm/tasks", headers=owner_headers, json={"title": "Done already"}).json()
    app_client.post(f"/api/v1/crm/tasks/{task['id']}/status", headers=owner_headers, json={"status": "done"})

    resp = app_client.post(
        f"/api/v1/crm/tasks/{task['id']}/status", headers=owner_headers, json={"status": "pending"}
    )
    assert resp.status_code == 422, resp.text


def test_cannot_edit_done_task(app_client, owner_headers):
    task = app_client.post("/api/v1/crm/tasks", headers=owner_headers, json={"title": "Freeze me"}).json()
    app_client.post(f"/api/v1/crm/tasks/{task['id']}/status", headers=owner_headers, json={"status": "done"})

    resp = app_client.patch(
        f"/api/v1/crm/tasks/{task['id']}", headers=owner_headers, json={"title": "Too late"}
    )
    assert resp.status_code == 422, resp.text


def test_cancel_task_with_reason(app_client, owner_headers):
    task = app_client.post("/api/v1/crm/tasks", headers=owner_headers, json={"title": "Skip this"}).json()

    resp = app_client.post(
        f"/api/v1/crm/tasks/{task['id']}/status",
        headers=owner_headers,
        json={"status": "cancelled", "cancelled_reason": "No longer needed"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "cancelled"
    assert body["cancelled_reason"] == "No longer needed"


def test_invalid_status_value_returns_400(app_client, owner_headers):
    task = app_client.post("/api/v1/crm/tasks", headers=owner_headers, json={"title": "Bad status"}).json()
    resp = app_client.post(
        f"/api/v1/crm/tasks/{task['id']}/status", headers=owner_headers, json={"status": "vanished"}
    )
    assert resp.status_code == 400, resp.text


def test_delete_task(app_client, owner_headers):
    task = app_client.post("/api/v1/crm/tasks", headers=owner_headers, json={"title": "Delete me"}).json()

    resp = app_client.delete(f"/api/v1/crm/tasks/{task['id']}", headers=owner_headers)
    assert resp.status_code == 204, resp.text

    fetched = app_client.get(f"/api/v1/crm/tasks/{task['id']}", headers=owner_headers)
    assert fetched.status_code == 404


def test_delete_task_requires_write_permission(app_client, owner_headers, viewer_headers):
    task = app_client.post("/api/v1/crm/tasks", headers=owner_headers, json={"title": "Protected"}).json()
    resp = app_client.delete(f"/api/v1/crm/tasks/{task['id']}", headers=viewer_headers)
    assert resp.status_code == 403


def test_recurring_task_requires_due_date_and_rule(app_client, owner_headers):
    resp = app_client.post(
        "/api/v1/crm/tasks", headers=owner_headers, json={"title": "Recurring but incomplete", "is_recurring": True}
    )
    assert resp.status_code == 422, resp.text


def test_recurring_task_with_due_date_and_rule_succeeds(app_client, owner_headers):
    resp = app_client.post(
        "/api/v1/crm/tasks",
        headers=owner_headers,
        json={
            "title": "Weekly report",
            "is_recurring": True,
            "recurrence_rule": "weekly",
            "due_date": "2026-08-01T09:00:00Z",
        },
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["is_recurring"] is True
