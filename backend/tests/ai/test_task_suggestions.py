"""Tests for Task Intelligence: SuggestTasksUseCase / POST /ai/tasks/suggest."""
from datetime import datetime, timedelta, timezone


def _types(items):
    return [r["recommendation_type"] for r in items]


def test_suggest_tasks_for_stale_lead(app_client, owner_headers, db_session, company):
    from modules.crm.infrastructure.models.lead import Lead

    stale = Lead(
        company_id=company.id, full_name="Stale Lead", source_channel="website", status="new",
        created_at=datetime.now(timezone.utc) - timedelta(hours=72),
    )
    db_session.add(stale)
    db_session.commit()

    items = app_client.post("/api/v1/ai/tasks/suggest", headers=owner_headers, json={}).json()["items"]
    task_recs = [r for r in items if r["recommendation_type"] == "task_suggestion"]
    assert any(r["related_entity_id"] == str(stale.id) for r in task_recs)


def test_no_task_suggested_for_fresh_lead(app_client, owner_headers, db_session, company):
    from modules.crm.infrastructure.models.lead import Lead

    fresh = Lead(company_id=company.id, full_name="Fresh Lead", source_channel="website", status="new")
    db_session.add(fresh)
    db_session.commit()

    items = app_client.post("/api/v1/ai/tasks/suggest", headers=owner_headers, json={}).json()["items"]
    task_recs = [r for r in items if r["recommendation_type"] == "task_suggestion"]
    assert not any(r["related_entity_id"] == str(fresh.id) for r in task_recs)


def test_suggest_task_for_unanswered_conversation(app_client, owner_headers, conversation):
    items = app_client.post("/api/v1/ai/tasks/suggest", headers=owner_headers, json={}).json()["items"]
    task_recs = [r for r in items if r["recommendation_type"] == "task_suggestion"]
    assert any(r["related_entity_id"] == str(conversation.id) for r in task_recs)


def test_assignee_suggestion_picks_lowest_workload(app_client, owner_headers, owner_user, rep_user, db_session, company):
    from modules.crm.infrastructure.models.task import Task

    for _ in range(3):
        db_session.add(Task(company_id=company.id, title="Busy owner task", assigned_to=owner_user.id, status="pending"))
    db_session.commit()

    items = app_client.post("/api/v1/ai/tasks/suggest", headers=owner_headers, json={}).json()["items"]
    rec = next(r for r in items if r["recommendation_type"] == "assignee_suggestion")
    assert rec["response"]["assignee_suggestion"] == str(rep_user.id)


def test_overdue_risk_detected_for_task_due_soon(app_client, owner_headers, db_session, company):
    from modules.crm.infrastructure.models.task import Task

    due_soon = Task(
        company_id=company.id, title="Due very soon", status="pending",
        due_date=datetime.now(timezone.utc) + timedelta(hours=2),
    )
    db_session.add(due_soon)
    db_session.commit()

    items = app_client.post("/api/v1/ai/tasks/suggest", headers=owner_headers, json={}).json()["items"]
    rec = next(r for r in items if r["recommendation_type"] == "overdue_risk")
    assert rec["related_entity_id"] == str(due_soon.id)


def test_no_overdue_risk_for_task_due_far_in_future(app_client, owner_headers, db_session, company):
    from modules.crm.infrastructure.models.task import Task

    far_future = Task(
        company_id=company.id, title="Due in a month", status="pending",
        due_date=datetime.now(timezone.utc) + timedelta(days=30),
    )
    db_session.add(far_future)
    db_session.commit()

    items = app_client.post("/api/v1/ai/tasks/suggest", headers=owner_headers, json={}).json()["items"]
    overdue_recs = [r for r in items if r["recommendation_type"] == "overdue_risk"]
    assert not any(r["related_entity_id"] == str(far_future.id) for r in overdue_recs)


def test_suggest_tasks_requires_write_permission(app_client, viewer_headers):
    resp = app_client.post("/api/v1/ai/tasks/suggest", headers=viewer_headers, json={})
    assert resp.status_code == 403


def test_suggest_tasks_writes_audit_and_event(app_client, owner_headers, db_session, company):
    from core.audit.models import AuditLog
    from core.events.models import EventLogEntry

    app_client.post("/api/v1/ai/tasks/suggest", headers=owner_headers, json={})

    entry = db_session.query(AuditLog).filter(AuditLog.action == "ai.tasks_suggested").first()
    assert entry is not None
    assert entry.company_id == company.id

    events = [e.event_name for e in db_session.query(EventLogEntry).all()]
    assert "TasksSuggested" in events
