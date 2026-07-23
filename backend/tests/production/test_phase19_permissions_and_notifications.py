"""Phase 19 (Stone Fabrication Workflow, Phase 3): finer-grained
priority/operator/stage permissions and the new in-app notification
surface for priority-urgent/operator-assigned/stage-changed moments."""
import pytest

from core.auth.models import ROLE_VIEWER, User, UserCompanyRole
from core.auth.security import create_access_token, hash_password


@pytest.fixture()
def viewer_user(db_session, company):
    user = User(email="viewer@production.test", password_hash=hash_password("Password123!"), full_name="Viewer User")
    db_session.add(user)
    db_session.flush()
    db_session.add(UserCompanyRole(user_id=user.id, company_id=company.id, role=ROLE_VIEWER))
    db_session.commit()
    return user


def _headers(user, company, role, module_permissions=None):
    token = create_access_token(
        user_id=user.id, active_company_id=company.id, role=role, module_permissions=module_permissions
    )
    return {"Authorization": f"Bearer {token}"}


# ── Finer-grained permissions ───────────────────────────────────────────────


def test_viewer_is_rejected_from_all_three_tracking_endpoints_by_default(
    app_client, viewer_user, company, approved_order, owner_headers
):
    work_order = app_client.post(
        "/api/v1/production", headers=owner_headers, json={"order_id": approved_order["id"]}
    ).json()
    viewer_headers = _headers(viewer_user, company, ROLE_VIEWER)

    assert app_client.post(
        f"/api/v1/production/{work_order['id']}/priority", headers=viewer_headers, json={"priority": "high"}
    ).status_code == 403
    assert app_client.post(
        f"/api/v1/production/{work_order['id']}/assign",
        headers=viewer_headers,
        json={"operator_user_id": str(viewer_user.id)},
    ).status_code == 403
    assert app_client.post(
        f"/api/v1/production/{work_order['id']}/stage", headers=viewer_headers, json={"stage_id": None}
    ).status_code == 403


def test_module_permission_override_grants_only_the_specific_action(
    app_client, viewer_user, company, approved_order, owner_headers
):
    """A viewer who is structurally below the rep-tier "write" rank for all
    three endpoints can still be granted just one of them individually via
    `module_permissions` -- this is the actual behavior Phase 19's
    permission split makes possible (it was previously all-or-nothing
    under a single `production:write`)."""
    work_order = app_client.post(
        "/api/v1/production", headers=owner_headers, json={"order_id": approved_order["id"]}
    ).json()
    priority_only_headers = _headers(
        viewer_user, company, ROLE_VIEWER, module_permissions={"production": ["production:priority:write"]}
    )

    priority_resp = app_client.post(
        f"/api/v1/production/{work_order['id']}/priority", headers=priority_only_headers, json={"priority": "high"}
    )
    assert priority_resp.status_code == 200, priority_resp.text

    assign_resp = app_client.post(
        f"/api/v1/production/{work_order['id']}/assign",
        headers=priority_only_headers,
        json={"operator_user_id": str(viewer_user.id)},
    )
    assert assign_resp.status_code == 403

    stage_resp = app_client.post(
        f"/api/v1/production/{work_order['id']}/stage", headers=priority_only_headers, json={"stage_id": None}
    )
    assert stage_resp.status_code == 403


# ── Notifications ────────────────────────────────────────────────────────────


def test_marking_priority_urgent_notifies_the_assigned_operator(
    app_client, owner_headers, approved_order, owner_user
):
    work_order = app_client.post(
        "/api/v1/production", headers=owner_headers, json={"order_id": approved_order["id"]}
    ).json()
    app_client.post(
        f"/api/v1/production/{work_order['id']}/assign",
        headers=owner_headers,
        json={"operator_user_id": str(owner_user.id)},
    )

    resp = app_client.post(
        f"/api/v1/production/{work_order['id']}/priority", headers=owner_headers, json={"priority": "urgent"}
    )
    assert resp.status_code == 200, resp.text

    notifications = app_client.get("/api/v1/production/notifications", headers=owner_headers).json()["items"]
    urgent = [n for n in notifications if n["notification_type"] == "priority_urgent"]
    assert len(urgent) == 1
    assert work_order["work_order_number"] in urgent[0]["message"]
    assert urgent[0]["work_order_id"] == work_order["id"]


def test_priority_change_without_an_assigned_operator_notifies_no_one(app_client, owner_headers, approved_order):
    work_order = app_client.post(
        "/api/v1/production", headers=owner_headers, json={"order_id": approved_order["id"]}
    ).json()

    app_client.post(
        f"/api/v1/production/{work_order['id']}/priority", headers=owner_headers, json={"priority": "urgent"}
    )

    notifications = app_client.get("/api/v1/production/notifications", headers=owner_headers).json()["items"]
    assert notifications == []


def test_assigning_an_operator_notifies_them(app_client, owner_headers, approved_order, owner_user):
    work_order = app_client.post(
        "/api/v1/production", headers=owner_headers, json={"order_id": approved_order["id"]}
    ).json()

    resp = app_client.post(
        f"/api/v1/production/{work_order['id']}/assign",
        headers=owner_headers,
        json={"operator_user_id": str(owner_user.id)},
    )
    assert resp.status_code == 200, resp.text

    notifications = app_client.get("/api/v1/production/notifications", headers=owner_headers).json()["items"]
    assigned = [n for n in notifications if n["notification_type"] == "operator_assigned"]
    assert len(assigned) == 1


def test_stage_change_notifies_the_assigned_operator(app_client, owner_headers, approved_order, owner_user):
    work_order = app_client.post(
        "/api/v1/production", headers=owner_headers, json={"order_id": approved_order["id"]}
    ).json()
    app_client.post(
        f"/api/v1/production/{work_order['id']}/assign",
        headers=owner_headers,
        json={"operator_user_id": str(owner_user.id)},
    )
    stages = app_client.get("/api/v1/production/stages", headers=owner_headers).json()["items"]
    cnc_stage = next(s for s in stages if s["name"] == "CNC")

    resp = app_client.post(
        f"/api/v1/production/{work_order['id']}/stage", headers=owner_headers, json={"stage_id": cnc_stage["id"]}
    )
    assert resp.status_code == 200, resp.text

    notifications = app_client.get("/api/v1/production/notifications", headers=owner_headers).json()["items"]
    stage_changed = [n for n in notifications if n["notification_type"] == "stage_changed"]
    assert len(stage_changed) == 1
    assert "CNC" in stage_changed[0]["message"]


def test_mark_notification_read_and_unread_only_filter(app_client, owner_headers, approved_order, owner_user):
    work_order = app_client.post(
        "/api/v1/production", headers=owner_headers, json={"order_id": approved_order["id"]}
    ).json()
    app_client.post(
        f"/api/v1/production/{work_order['id']}/assign",
        headers=owner_headers,
        json={"operator_user_id": str(owner_user.id)},
    )

    notifications = app_client.get("/api/v1/production/notifications", headers=owner_headers).json()["items"]
    assert len(notifications) == 1
    notification_id = notifications[0]["id"]

    read_resp = app_client.post(f"/api/v1/production/notifications/{notification_id}/read", headers=owner_headers)
    assert read_resp.status_code == 200
    assert read_resp.json()["read_at"] is not None

    unread = app_client.get(
        "/api/v1/production/notifications", headers=owner_headers, params={"unread_only": True}
    ).json()["items"]
    assert unread == []
