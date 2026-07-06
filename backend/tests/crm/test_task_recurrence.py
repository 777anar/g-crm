"""Tests for recurring task next-occurrence spawning (UpdateTaskStatusUseCase
._spawn_next_occurrence in modules/crm/application/use_cases/task_use_cases.py)."""


def _series(app_client, headers, task_id):
    return app_client.get(f"/api/v1/crm/tasks/{task_id}/series", headers=headers).json()["items"]


def test_non_recurring_task_completion_does_not_spawn(app_client, owner_headers):
    task = app_client.post("/api/v1/crm/tasks", headers=owner_headers, json={"title": "One-off"}).json()
    app_client.post(f"/api/v1/crm/tasks/{task['id']}/status", headers=owner_headers, json={"status": "done"})

    series = _series(app_client, owner_headers, task["id"])
    assert len(series) == 1


def test_weekly_recurrence_spawns_next_occurrence(app_client, owner_headers):
    task = app_client.post(
        "/api/v1/crm/tasks",
        headers=owner_headers,
        json={
            "title": "Weekly sync",
            "is_recurring": True,
            "recurrence_rule": "weekly",
            "due_date": "2026-08-01T09:00:00Z",
        },
    ).json()

    resp = app_client.post(f"/api/v1/crm/tasks/{task['id']}/status", headers=owner_headers, json={"status": "done"})
    assert resp.status_code == 200

    series = _series(app_client, owner_headers, task["id"])
    assert len(series) == 2
    next_task = next(t for t in series if t["id"] != task["id"])
    assert next_task["status"] == "pending"
    assert next_task["due_date"].startswith("2026-08-08")
    assert next_task["series_id"] == task["id"]
    assert next_task["is_recurring"] is True
    assert next_task["recurrence_rule"] == "weekly"


def test_monthly_recurrence_clamps_day_to_month_end(app_client, owner_headers):
    task = app_client.post(
        "/api/v1/crm/tasks",
        headers=owner_headers,
        json={
            "title": "Month-end close",
            "is_recurring": True,
            "recurrence_rule": "monthly",
            "due_date": "2026-01-31T09:00:00Z",
        },
    ).json()

    app_client.post(f"/api/v1/crm/tasks/{task['id']}/status", headers=owner_headers, json={"status": "done"})

    series = _series(app_client, owner_headers, task["id"])
    next_task = next(t for t in series if t["id"] != task["id"])
    # 2026 is not a leap year -- Jan 31 + 1 month clamps to Feb 28.
    assert next_task["due_date"].startswith("2026-02-28")


def test_daily_recurrence_with_interval(app_client, owner_headers):
    task = app_client.post(
        "/api/v1/crm/tasks",
        headers=owner_headers,
        json={
            "title": "Every 3 days",
            "is_recurring": True,
            "recurrence_rule": "daily",
            "recurrence_interval": 3,
            "due_date": "2026-08-01T09:00:00Z",
        },
    ).json()

    app_client.post(f"/api/v1/crm/tasks/{task['id']}/status", headers=owner_headers, json={"status": "done"})

    series = _series(app_client, owner_headers, task["id"])
    next_task = next(t for t in series if t["id"] != task["id"])
    assert next_task["due_date"].startswith("2026-08-04")


def test_recurrence_end_date_stops_spawning(app_client, owner_headers):
    task = app_client.post(
        "/api/v1/crm/tasks",
        headers=owner_headers,
        json={
            "title": "Ends soon",
            "is_recurring": True,
            "recurrence_rule": "weekly",
            "due_date": "2026-08-01T09:00:00Z",
            "recurrence_end_date": "2026-08-05",
        },
    ).json()

    app_client.post(f"/api/v1/crm/tasks/{task['id']}/status", headers=owner_headers, json={"status": "done"})

    series = _series(app_client, owner_headers, task["id"])
    assert len(series) == 1


def test_recurrence_chain_keeps_series_id_pointing_to_root(app_client, owner_headers):
    root = app_client.post(
        "/api/v1/crm/tasks",
        headers=owner_headers,
        json={
            "title": "Chain me",
            "is_recurring": True,
            "recurrence_rule": "daily",
            "due_date": "2026-08-01T09:00:00Z",
        },
    ).json()

    app_client.post(f"/api/v1/crm/tasks/{root['id']}/status", headers=owner_headers, json={"status": "done"})
    series = _series(app_client, owner_headers, root["id"])
    instance_2 = next(t for t in series if t["id"] != root["id"])

    app_client.post(f"/api/v1/crm/tasks/{instance_2['id']}/status", headers=owner_headers, json={"status": "done"})
    series_after = _series(app_client, owner_headers, instance_2["id"])

    assert len(series_after) == 3
    instance_3 = next(t for t in series_after if t["id"] not in (root["id"], instance_2["id"]))
    assert instance_3["series_id"] == root["id"]


def test_recurring_reminder_preserves_lead_time(app_client, owner_headers):
    """remind_at should shift by the same amount as due_date -- a "remind
    me 1 day before" setting stays 1 day before on every future occurrence."""
    task = app_client.post(
        "/api/v1/crm/tasks",
        headers=owner_headers,
        json={
            "title": "Remind ahead",
            "is_recurring": True,
            "recurrence_rule": "weekly",
            "due_date": "2026-08-08T09:00:00Z",
            "remind_at": "2026-08-07T09:00:00Z",
        },
    ).json()

    app_client.post(f"/api/v1/crm/tasks/{task['id']}/status", headers=owner_headers, json={"status": "done"})

    series = _series(app_client, owner_headers, task["id"])
    next_task = next(t for t in series if t["id"] != task["id"])
    assert next_task["due_date"].startswith("2026-08-15")
    assert next_task["remind_at"].startswith("2026-08-14")
