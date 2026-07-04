"""Tests for the Reports module."""


def test_executive_dashboard_kpis(app_client, owner_headers, completed_order, lost_customer, lead):
    resp = app_client.get("/api/v1/reports/executive", headers=owner_headers, params={"period": "90d"})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["kpis"]["orders_created"] == 1
    assert body["kpis"]["revenue"] == "442.50"
    assert body["kpis"]["profit"] == "192.50"
    assert body["kpis"]["lost_customers"] == 1
    assert body["kpis"]["leads_captured"] == 1
    assert any(row["status"] == "completed" and row["count"] == 1 for row in body["orders_by_status"])
    assert len(body["revenue_trend"]) == 1


def test_executive_dashboard_empty_period_has_zeroed_kpis(app_client, owner_headers, company):
    resp = app_client.get("/api/v1/reports/executive", headers=owner_headers, params={"period": "7d"})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["kpis"]["revenue"] == "0"
    assert body["kpis"]["orders_created"] == 0
    assert body["customers_by_status"] == []


def test_sales_analytics_win_rate_and_top_customers(app_client, owner_headers, accepted_quote):
    resp = app_client.get("/api/v1/reports/sales", headers=owner_headers, params={"period": "90d"})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["kpis"]["total_quotes"] == 1
    assert body["kpis"]["accepted_quotes"] == 1
    assert body["kpis"]["win_rate"] == 100.0
    assert body["top_customers"][0]["customer_name"] == "Test Customer"
    assert any(r["project_type"] == "kitchen" for r in body["revenue_by_project_type"])


def test_production_analytics_reflects_order_status(app_client, owner_headers, order_in_production):
    resp = app_client.get("/api/v1/reports/production", headers=owner_headers, params={"period": "90d"})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["kpis"]["orders_in_production"] == 1
    assert body["kpis"]["orders_entered_production"] == 1
    assert any(r["status"] == "in_production" and r["count"] == 1 for r in body["order_status_breakdown"])


def test_production_analytics_cycle_time_for_completed_order(app_client, owner_headers, completed_order):
    resp = app_client.get("/api/v1/reports/production", headers=owner_headers, params={"period": "90d"})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["kpis"]["orders_completed_production"] == 1
    assert body["kpis"]["avg_production_cycle_days"] is not None


def test_installation_analytics_reflects_completed_job(app_client, owner_headers, completed_installation_job):
    resp = app_client.get("/api/v1/reports/installation", headers=owner_headers, params={"period": "90d"})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["kpis"]["jobs_created"] == 1
    assert body["kpis"]["jobs_completed"] == 1
    assert body["kpis"]["avg_installation_hours"] is not None
    assert any(r["count"] == 1 for r in body["daily_installations"])
    assert len(body["crew_productivity"]) == 1
    assert body["crew_productivity"][0]["crew_name"] == "Test Crew"
    assert body["crew_productivity"][0]["completed_count"] == 1


def test_finance_analytics_revenue_and_margin(app_client, owner_headers, completed_order):
    resp = app_client.get("/api/v1/reports/finance", headers=owner_headers, params={"period": "90d"})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["kpis"]["revenue"] == "442.50"
    assert body["kpis"]["profit"] == "192.50"
    assert body["kpis"]["recognized_revenue"] == "442.50"
    assert body["kpis"]["orders_count"] == 1
    assert any(r["currency"] == "AZN" for r in body["revenue_by_currency"])


def test_custom_date_range_overrides_period(app_client, owner_headers, completed_order):
    resp = app_client.get(
        "/api/v1/reports/finance",
        headers=owner_headers,
        params={"date_from": "2000-01-01", "date_to": "2000-01-02"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["kpis"]["orders_count"] == 0


def test_export_pdf(app_client, owner_headers, completed_order):
    resp = app_client.get(
        "/api/v1/reports/finance/export/pdf", headers=owner_headers, params={"period": "90d"}
    )
    assert resp.status_code == 200, resp.text
    assert resp.headers["content-type"] == "application/pdf"
    assert resp.content[:4] == b"%PDF"


def test_export_excel(app_client, owner_headers, completed_order):
    resp = app_client.get(
        "/api/v1/reports/executive/export/excel", headers=owner_headers, params={"period": "90d"}
    )
    assert resp.status_code == 200, resp.text
    assert resp.headers["content-type"] == (
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    assert resp.content[:2] == b"PK"


def test_export_unknown_report_type_returns_400(app_client, owner_headers, company):
    resp = app_client.get("/api/v1/reports/bogus/export/pdf", headers=owner_headers)
    assert resp.status_code == 400


def test_reports_requires_auth(app_client):
    resp = app_client.get("/api/v1/reports/executive")
    assert resp.status_code == 401
