"""Tests for GET /ai/dashboard -- lead score distribution, sales
probability, pipeline health, at-risk customers, follow-ups, daily
recommendations, recent activity, and usage statistics."""


def test_dashboard_returns_all_widgets(app_client, owner_headers, lead):
    app_client.post(f"/api/v1/ai/leads/{lead['id']}/analyze", headers=owner_headers, json={})

    resp = app_client.get("/api/v1/ai/dashboard", headers=owner_headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    for key in (
        "lead_score_distribution", "avg_win_probability", "pipeline_health",
        "at_risk_customers", "follow_up_recommendations", "daily_recommendations",
        "recent_activity", "usage_stats",
    ):
        assert key in body


def test_lead_score_distribution_buckets_the_analyzed_lead(app_client, owner_headers, lead):
    items = app_client.post(f"/api/v1/ai/leads/{lead['id']}/analyze", headers=owner_headers, json={}).json()["items"]
    score = next(r for r in items if r["recommendation_type"] == "lead_score")["response"]["score"]

    dashboard = app_client.get("/api/v1/ai/dashboard", headers=owner_headers).json()
    total_bucketed = sum(dashboard["lead_score_distribution"].values())
    assert total_bucketed == 1
    for low, high, label in ((0, 25, "0-25"), (26, 50, "26-50"), (51, 75, "51-75"), (76, 100, "76-100")):
        if low <= score <= high:
            assert dashboard["lead_score_distribution"][label] == 1


def test_avg_win_probability_computed(app_client, owner_headers, lead):
    app_client.post(f"/api/v1/ai/leads/{lead['id']}/analyze", headers=owner_headers, json={})
    dashboard = app_client.get("/api/v1/ai/dashboard", headers=owner_headers).json()
    assert dashboard["avg_win_probability"] is not None
    assert 0.0 <= dashboard["avg_win_probability"] <= 1.0


def test_at_risk_customers_includes_pending_missing_info(app_client, owner_headers, bare_lead):
    app_client.post(f"/api/v1/ai/leads/{bare_lead['id']}/analyze", headers=owner_headers, json={})
    dashboard = app_client.get("/api/v1/ai/dashboard", headers=owner_headers).json()
    assert any(r["recommendation_type"] == "missing_info" for r in dashboard["at_risk_customers"])


def test_follow_up_recommendations_lists_pending_follow_ups(app_client, owner_headers, lead):
    app_client.post(f"/api/v1/ai/leads/{lead['id']}/analyze", headers=owner_headers, json={})
    dashboard = app_client.get("/api/v1/ai/dashboard", headers=owner_headers).json()
    assert len(dashboard["follow_up_recommendations"]) == 1


def test_reviewed_follow_up_disappears_from_recommendations_widget(app_client, owner_headers, lead):
    items = app_client.post(f"/api/v1/ai/leads/{lead['id']}/analyze", headers=owner_headers, json={}).json()["items"]
    follow_up_id = next(r["id"] for r in items if r["recommendation_type"] == "follow_up_recommendation")
    app_client.post(f"/api/v1/ai/recommendations/{follow_up_id}/review", headers=owner_headers, json={"decision": "accept"})

    dashboard = app_client.get("/api/v1/ai/dashboard", headers=owner_headers).json()
    assert dashboard["follow_up_recommendations"] == []


def test_daily_recommendations_includes_recommendations_created_today(app_client, owner_headers, lead):
    app_client.post(f"/api/v1/ai/leads/{lead['id']}/analyze", headers=owner_headers, json={})
    dashboard = app_client.get("/api/v1/ai/dashboard", headers=owner_headers).json()
    assert len(dashboard["daily_recommendations"]) >= 5


def test_recent_activity_ordered_newest_first(app_client, owner_headers, lead, bare_lead):
    app_client.post(f"/api/v1/ai/leads/{lead['id']}/analyze", headers=owner_headers, json={})
    app_client.post(f"/api/v1/ai/leads/{bare_lead['id']}/analyze", headers=owner_headers, json={})

    dashboard = app_client.get("/api/v1/ai/dashboard", headers=owner_headers).json()
    timestamps = [a["created_at"] for a in dashboard["recent_activity"]]
    assert timestamps == sorted(timestamps, reverse=True)


def test_usage_stats_counts_and_acceptance_rate(app_client, owner_headers, lead):
    items = app_client.post(f"/api/v1/ai/leads/{lead['id']}/analyze", headers=owner_headers, json={}).json()["items"]
    app_client.post(f"/api/v1/ai/recommendations/{items[0]['id']}/review", headers=owner_headers, json={"decision": "accept"})
    app_client.post(f"/api/v1/ai/recommendations/{items[1]['id']}/review", headers=owner_headers, json={"decision": "reject"})

    dashboard = app_client.get("/api/v1/ai/dashboard", headers=owner_headers).json()
    stats = dashboard["usage_stats"]
    assert stats["total_recommendations"] == len(items)
    assert stats["status_counts"]["accepted"] == 1
    assert stats["status_counts"]["rejected"] == 1
    assert stats["acceptance_rate"] == 0.5
    assert stats["provider_counts"]["mock"] == len(items)
    assert stats["avg_execution_time_ms"] is not None


def test_pipeline_health_reports_active_customers(app_client, owner_headers, customer):
    dashboard = app_client.get("/api/v1/ai/dashboard", headers=owner_headers).json()
    assert dashboard["pipeline_health"]["active_pipeline_count"] >= 1


def test_dashboard_requires_read_permission(app_client, viewer_headers):
    resp = app_client.get("/api/v1/ai/dashboard", headers=viewer_headers)
    assert resp.status_code == 200
