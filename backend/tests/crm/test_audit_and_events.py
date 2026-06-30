"""Verifies requirement #4: every CRM action creates both an audit log entry
and a domain event."""
from core.audit.models import AuditLog
from core.events.models import EventLogEntry


def _audit_actions(db_session, entity_type):
    rows = db_session.query(AuditLog).filter(AuditLog.entity_type == entity_type).all()
    return [r.action for r in rows]


def _event_names(db_session):
    rows = db_session.query(EventLogEntry).all()
    return [r.event_name for r in rows]


def test_create_customer_writes_audit_and_event(app_client, owner_headers, db_session):
    app_client.post("/api/v1/crm/customers", headers=owner_headers, json={"name": "Audit Co", "type": "business"})

    assert "customer.created" in _audit_actions(db_session, "customer")
    assert "CustomerCreated" in _event_names(db_session)


def test_update_customer_writes_audit_and_event(app_client, owner_headers, db_session):
    created = app_client.post(
        "/api/v1/crm/customers", headers=owner_headers, json={"name": "Audit Update Co", "type": "business"}
    ).json()
    app_client.patch(f"/api/v1/crm/customers/{created['id']}", headers=owner_headers, json={"name": "Renamed"})

    assert "customer.updated" in _audit_actions(db_session, "customer")
    assert "CustomerUpdated" in _event_names(db_session)


def test_archive_customer_writes_audit_and_event(app_client, owner_headers, db_session):
    created = app_client.post(
        "/api/v1/crm/customers", headers=owner_headers, json={"name": "Audit Archive Co", "type": "business"}
    ).json()
    app_client.delete(f"/api/v1/crm/customers/{created['id']}", headers=owner_headers)

    assert "customer.archived" in _audit_actions(db_session, "customer")
    assert "CustomerArchived" in _event_names(db_session)


def test_add_note_writes_audit_and_event(app_client, owner_headers, db_session):
    created = app_client.post(
        "/api/v1/crm/customers", headers=owner_headers, json={"name": "Audit Note Co", "type": "business"}
    ).json()
    app_client.post(
        f"/api/v1/crm/customers/{created['id']}/notes", headers=owner_headers, json={"body": "Audited note."}
    )

    assert "customer.note_added" in _audit_actions(db_session, "customer")
    assert "CustomerNoteAdded" in _event_names(db_session)


def test_create_lead_writes_audit_and_event(app_client, owner_headers, db_session):
    app_client.post(
        "/api/v1/crm/leads", headers=owner_headers, json={"full_name": "Audit Lead", "source_channel": "phone_call"}
    )

    assert "lead.created" in _audit_actions(db_session, "lead")
    assert "LeadCreated" in _event_names(db_session)


def test_convert_lead_writes_audit_and_event(app_client, owner_headers, db_session):
    lead = app_client.post(
        "/api/v1/crm/leads", headers=owner_headers, json={"full_name": "Audit Convert Lead", "source_channel": "phone_call"}
    ).json()
    app_client.post(f"/api/v1/crm/leads/{lead['id']}/convert", headers=owner_headers)

    assert "lead.converted" in _audit_actions(db_session, "lead")
    assert "LeadConverted" in _event_names(db_session)


def test_audit_entries_record_actor_and_company(app_client, owner_headers, db_session, owner_user, company):
    app_client.post("/api/v1/crm/customers", headers=owner_headers, json={"name": "Actor Co", "type": "business"})

    entry = db_session.query(AuditLog).filter(AuditLog.action == "customer.created").first()
    assert entry is not None
    assert entry.actor_user_id == owner_user.id
    assert entry.company_id == company.id
    assert entry.module == "crm"


def test_events_introspection_endpoint_returns_logged_events(app_client, owner_headers):
    app_client.post("/api/v1/crm/customers", headers=owner_headers, json={"name": "Introspect Co", "type": "business"})

    response = app_client.get("/api/v1/core/events", headers=owner_headers, params={"event_name": "CustomerCreated"})
    assert response.status_code == 200
    events = response.json()
    assert len(events) >= 1
    assert events[0]["event_name"] == "CustomerCreated"
    assert events[0]["published_by_module"] == "crm"
