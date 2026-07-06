"""Search, filter, sort, multi-company isolation, and audit/event coverage
for Tasks & Reminders."""


def test_search_tasks_by_title(app_client, owner_headers):
    app_client.post("/api/v1/crm/tasks", headers=owner_headers, json={"title": "Call Rashad Aliyev"})
    app_client.post("/api/v1/crm/tasks", headers=owner_headers, json={"title": "Email Leyla Huseynova"})

    resp = app_client.get("/api/v1/crm/tasks", headers=owner_headers, params={"search": "Rashad"})
    items = resp.json()["items"]
    assert len(items) == 1
    assert items[0]["title"] == "Call Rashad Aliyev"


def test_search_tasks_by_description(app_client, owner_headers):
    app_client.post(
        "/api/v1/crm/tasks",
        headers=owner_headers,
        json={"title": "Follow up", "description": "About the marble countertop order"},
    )
    resp = app_client.get("/api/v1/crm/tasks", headers=owner_headers, params={"search": "countertop"})
    assert len(resp.json()["items"]) == 1


def test_filter_tasks_by_status(app_client, owner_headers):
    a = app_client.post("/api/v1/crm/tasks", headers=owner_headers, json={"title": "Stays pending"}).json()
    b = app_client.post("/api/v1/crm/tasks", headers=owner_headers, json={"title": "Goes to done"}).json()
    app_client.post(f"/api/v1/crm/tasks/{b['id']}/status", headers=owner_headers, json={"status": "done"})

    resp = app_client.get("/api/v1/crm/tasks", headers=owner_headers, params={"status": "pending"})
    ids = [t["id"] for t in resp.json()["items"]]
    assert a["id"] in ids
    assert b["id"] not in ids


def test_filter_tasks_by_priority(app_client, owner_headers):
    app_client.post("/api/v1/crm/tasks", headers=owner_headers, json={"title": "Low one", "priority": "low"})
    app_client.post("/api/v1/crm/tasks", headers=owner_headers, json={"title": "Urgent one", "priority": "urgent"})

    resp = app_client.get("/api/v1/crm/tasks", headers=owner_headers, params={"priority": "urgent"})
    items = resp.json()["items"]
    assert len(items) == 1
    assert items[0]["title"] == "Urgent one"


def test_filter_tasks_by_assigned_to(app_client, owner_headers, rep_user, owner_user):
    app_client.post(
        "/api/v1/crm/tasks", headers=owner_headers, json={"title": "For rep", "assigned_to": str(rep_user.id)}
    )
    app_client.post(
        "/api/v1/crm/tasks", headers=owner_headers, json={"title": "For owner", "assigned_to": str(owner_user.id)}
    )

    resp = app_client.get("/api/v1/crm/tasks", headers=owner_headers, params={"assigned_to": str(rep_user.id)})
    items = resp.json()["items"]
    assert len(items) == 1
    assert items[0]["title"] == "For rep"


def test_exclude_terminal_filter(app_client, owner_headers):
    open_task = app_client.post("/api/v1/crm/tasks", headers=owner_headers, json={"title": "Open"}).json()
    closed_task = app_client.post("/api/v1/crm/tasks", headers=owner_headers, json={"title": "Closed"}).json()
    app_client.post(
        f"/api/v1/crm/tasks/{closed_task['id']}/status", headers=owner_headers, json={"status": "cancelled"}
    )

    resp = app_client.get("/api/v1/crm/tasks", headers=owner_headers, params={"exclude_terminal": True})
    ids = [t["id"] for t in resp.json()["items"]]
    assert open_task["id"] in ids
    assert closed_task["id"] not in ids


def test_sort_tasks_by_due_date_ascending(app_client, owner_headers):
    app_client.post(
        "/api/v1/crm/tasks", headers=owner_headers, json={"title": "Later", "due_date": "2026-09-01T00:00:00Z"}
    )
    app_client.post(
        "/api/v1/crm/tasks", headers=owner_headers, json={"title": "Sooner", "due_date": "2026-08-01T00:00:00Z"}
    )

    resp = app_client.get("/api/v1/crm/tasks", headers=owner_headers, params={"sort": "due_date"})
    titles = [t["title"] for t in resp.json()["items"]]
    assert titles == ["Sooner", "Later"]


def test_sort_tasks_falls_back_to_created_at_for_unknown_field(app_client, owner_headers):
    app_client.post("/api/v1/crm/tasks", headers=owner_headers, json={"title": "Fallback"})
    resp = app_client.get("/api/v1/crm/tasks", headers=owner_headers, params={"sort": "secret_column"})
    assert resp.status_code == 200


def test_tasks_isolated_by_company(app_client, db_session, owner_headers, company):
    from core.auth.models import ROLE_OWNER, User, UserCompanyRole
    from core.auth.security import create_access_token, hash_password
    from core.companies.models import Company

    created = app_client.post("/api/v1/crm/tasks", headers=owner_headers, json={"title": "Isolated task"}).json()

    other_company = Company(name="KORONA PREMIUM", slug="korona-premium-tasks-test", enabled_modules=["crm"])
    db_session.add(other_company)
    db_session.flush()
    other_user = User(email="other-owner@tasks.test", password_hash=hash_password("x"), full_name="Other Owner")
    db_session.add(other_user)
    db_session.flush()
    db_session.add(UserCompanyRole(user_id=other_user.id, company_id=other_company.id, role=ROLE_OWNER))
    db_session.commit()
    other_token = create_access_token(user_id=other_user.id, active_company_id=other_company.id, role=ROLE_OWNER)
    other_headers = {"Authorization": f"Bearer {other_token}"}

    response = app_client.get(f"/api/v1/crm/tasks/{created['id']}", headers=other_headers)
    assert response.status_code == 404

    other_company_tasks = app_client.get("/api/v1/crm/tasks", headers=other_headers).json()
    assert created["id"] not in [t["id"] for t in other_company_tasks["items"]]


def test_task_creation_writes_audit_and_event(app_client, owner_headers, db_session, owner_user, company):
    from core.audit.models import AuditLog
    from core.events.models import EventLogEntry

    app_client.post("/api/v1/crm/tasks", headers=owner_headers, json={"title": "Audited task"})

    entry = db_session.query(AuditLog).filter(AuditLog.action == "task.created").first()
    assert entry is not None
    assert entry.actor_user_id == owner_user.id
    assert entry.company_id == company.id
    assert entry.module == "crm"

    events = [e.event_name for e in db_session.query(EventLogEntry).all()]
    assert "TaskCreated" in events


def test_task_status_change_and_deletion_write_audit_and_events(app_client, owner_headers, db_session):
    from core.audit.models import AuditLog
    from core.events.models import EventLogEntry

    task = app_client.post("/api/v1/crm/tasks", headers=owner_headers, json={"title": "Full lifecycle"}).json()
    app_client.post(f"/api/v1/crm/tasks/{task['id']}/status", headers=owner_headers, json={"status": "done"})
    app_client.delete(f"/api/v1/crm/tasks/{task['id']}", headers=owner_headers)

    actions = [r.action for r in db_session.query(AuditLog).filter(AuditLog.entity_type == "task").all()]
    assert "task.created" in actions
    assert "task.status_changed" in actions
    assert "task.deleted" in actions

    events = [e.event_name for e in db_session.query(EventLogEntry).all()]
    assert "TaskCompleted" in events
    assert "TaskDeleted" in events
