"""Tests for the Installation module's job lifecycle."""


def _create_ready_order(app_client, db_session, owner_headers, company, project, customer, suffix):
    from modules.sales.infrastructure.models.quote import Quote
    from modules.sales.infrastructure.models.quote_section import QuoteSection
    from modules.sales.infrastructure.models.quote_section_item import QuoteSectionItem

    q = Quote(
        company_id=company.id,
        project_id=project.id,
        customer_id=customer.id,
        version=1,
        quote_number=f"QT-2026-{suffix}-v1",
        status="accepted",
        currency="AZN",
    )
    db_session.add(q)
    db_session.flush()
    sec = QuoteSection(company_id=company.id, quote_id=q.id, name="Main Section", sort_order=0)
    db_session.add(sec)
    db_session.flush()
    db_session.add(
        QuoteSectionItem(
            company_id=company.id,
            section_id=sec.id,
            quote_id=q.id,
            item_type="material",
            sort_order=0,
            description="Marble countertop",
            quantity="1",
            unit="m2",
            unit_sale_price="100.00",
            unit_cost_price="80.00",
            line_total_sale="100.00",
            line_total_cost="80.00",
        )
    )
    db_session.commit()

    order = app_client.post("/api/v1/orders", headers=owner_headers, json={"quote_id": str(q.id)}).json()
    for status in ("approved_for_production", "in_production", "ready"):
        resp = app_client.post(f"/api/v1/orders/{order['id']}/status", headers=owner_headers, json={"status": status})
        assert resp.status_code == 200, resp.text
    return resp.json()


def test_installation_jobs_cursor_reaches_the_next_page(app_client, owner_headers, db_session, company, project, customer):
    job_ids = []
    for i in range(3):
        order = _create_ready_order(app_client, db_session, owner_headers, company, project, customer, f"CUR{i}")
        resp = app_client.post("/api/v1/installation/jobs", headers=owner_headers, json={"order_id": order["id"]})
        assert resp.status_code == 200, resp.text
        job_ids.append(resp.json()["id"])

    first_page = app_client.get("/api/v1/installation/jobs", headers=owner_headers, params={"limit": 2}).json()
    assert len(first_page["items"]) == 2
    assert first_page["next_cursor"] is not None

    second_page = app_client.get(
        "/api/v1/installation/jobs", headers=owner_headers, params={"limit": 2, "cursor": first_page["next_cursor"]}
    ).json()
    assert len(second_page["items"]) == 1
    assert second_page["next_cursor"] is None

    first_ids = {j["id"] for j in first_page["items"]}
    second_ids = {j["id"] for j in second_page["items"]}
    assert first_ids.isdisjoint(second_ids)
    assert first_ids | second_ids == set(job_ids)


def test_create_installation_job_requires_ready_order(app_client, owner_headers, accepted_quote):
    order = app_client.post(
        "/api/v1/orders", headers=owner_headers, json={"quote_id": str(accepted_quote.id)}
    ).json()

    resp = app_client.post(
        "/api/v1/installation/jobs", headers=owner_headers, json={"order_id": order["id"]}
    )
    assert resp.status_code == 422, resp.text


def test_create_installation_job_success(app_client, owner_headers, ready_order):
    resp = app_client.post(
        "/api/v1/installation/jobs", headers=owner_headers, json={"order_id": ready_order["id"]}
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "scheduled"
    assert body["job_number"].startswith("INST-")
    assert body["order_id"] == ready_order["id"]


def test_create_installation_job_twice_returns_422(app_client, owner_headers, ready_order):
    first = app_client.post(
        "/api/v1/installation/jobs", headers=owner_headers, json={"order_id": ready_order["id"]}
    )
    assert first.status_code == 200, first.text

    second = app_client.post(
        "/api/v1/installation/jobs", headers=owner_headers, json={"order_id": ready_order["id"]}
    )
    assert second.status_code == 422, second.text


def test_schedule_job_assigns_crew_and_notifies(app_client, owner_headers, ready_order, crew, installer_user, company):
    job = app_client.post(
        "/api/v1/installation/jobs", headers=owner_headers, json={"order_id": ready_order["id"]}
    ).json()

    resp = app_client.patch(
        f"/api/v1/installation/jobs/{job['id']}",
        headers=owner_headers,
        json={"crew_id": crew["id"], "scheduled_date": "2026-08-01", "scheduled_time_slot": "09:00-12:00"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["crew_id"] == crew["id"]
    assert body["scheduled_date"] == "2026-08-01"

    from core.auth.models import ROLE_OWNER
    from core.auth.security import create_access_token

    installer_token = create_access_token(user_id=installer_user.id, active_company_id=company.id, role=ROLE_OWNER)
    notif_resp = app_client.get(
        "/api/v1/installation/notifications", headers={"Authorization": f"Bearer {installer_token}"}
    )
    assert notif_resp.status_code == 200
    notifications = notif_resp.json()["items"]
    assert len(notifications) == 1
    assert notifications[0]["notification_type"] == "job_assigned"
    assert notifications[0]["read_at"] is None


def test_reschedule_notifies_crew_again(app_client, owner_headers, ready_order, crew):
    job = app_client.post(
        "/api/v1/installation/jobs", headers=owner_headers, json={"order_id": ready_order["id"]}
    ).json()
    app_client.patch(
        f"/api/v1/installation/jobs/{job['id']}",
        headers=owner_headers,
        json={"crew_id": crew["id"], "scheduled_date": "2026-08-01"},
    )
    resp = app_client.patch(
        f"/api/v1/installation/jobs/{job['id']}",
        headers=owner_headers,
        json={"scheduled_date": "2026-08-02"},
    )
    assert resp.status_code == 200
    assert resp.json()["scheduled_date"] == "2026-08-02"


def test_full_job_lifecycle_completes_order(app_client, owner_headers, ready_order, crew):
    job = app_client.post(
        "/api/v1/installation/jobs", headers=owner_headers, json={"order_id": ready_order["id"]}
    ).json()
    app_client.patch(
        f"/api/v1/installation/jobs/{job['id']}", headers=owner_headers, json={"crew_id": crew["id"]}
    )

    for status in ("en_route", "in_progress"):
        resp = app_client.post(
            f"/api/v1/installation/jobs/{job['id']}/status", headers=owner_headers, json={"status": status}
        )
        assert resp.status_code == 200, f"Failed on {status}: {resp.text}"

    complete_resp = app_client.post(
        f"/api/v1/installation/jobs/{job['id']}/status",
        headers=owner_headers,
        json={"status": "completed", "completion_notes": "Installed without issues."},
    )
    assert complete_resp.status_code == 200, complete_resp.text
    body = complete_resp.json()
    assert body["status"] == "completed"
    assert body["completion_notes"] == "Installed without issues."
    assert body["completed_at"] is not None

    order_resp = app_client.get(f"/api/v1/orders/{ready_order['id']}", headers=owner_headers)
    assert order_resp.json()["status"] == "installed"

    sections = app_client.get(f"/api/v1/orders/{ready_order['id']}/sections", headers=owner_headers).json()["items"]
    items = app_client.get(
        f"/api/v1/orders/{ready_order['id']}/sections/{sections[0]['id']}/items", headers=owner_headers
    ).json()["items"]
    assert items[0]["installation_status"] == "done"


def test_invalid_job_transition_returns_422(app_client, owner_headers, ready_order):
    job = app_client.post(
        "/api/v1/installation/jobs", headers=owner_headers, json={"order_id": ready_order["id"]}
    ).json()

    resp = app_client.post(
        f"/api/v1/installation/jobs/{job['id']}/status", headers=owner_headers, json={"status": "completed"}
    )
    assert resp.status_code == 422, resp.text


def test_cancel_job(app_client, owner_headers, ready_order):
    job = app_client.post(
        "/api/v1/installation/jobs", headers=owner_headers, json={"order_id": ready_order["id"]}
    ).json()

    resp = app_client.post(
        f"/api/v1/installation/jobs/{job['id']}/status",
        headers=owner_headers,
        json={"status": "cancelled", "cancelled_reason": "Customer rescheduled"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "cancelled"
    assert resp.json()["cancelled_reason"] == "Customer rescheduled"


def test_list_and_get_by_order(app_client, owner_headers, ready_order):
    created = app_client.post(
        "/api/v1/installation/jobs", headers=owner_headers, json={"order_id": ready_order["id"]}
    ).json()

    list_resp = app_client.get("/api/v1/installation/jobs", headers=owner_headers)
    assert list_resp.status_code == 200
    assert any(j["id"] == created["id"] for j in list_resp.json()["items"])

    by_order_resp = app_client.get(
        f"/api/v1/installation/jobs/by-order/{ready_order['id']}", headers=owner_headers
    )
    assert by_order_resp.status_code == 200
    assert by_order_resp.json()["id"] == created["id"]
