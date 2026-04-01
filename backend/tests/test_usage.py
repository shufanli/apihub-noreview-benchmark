"""Tests for usage endpoints."""
import pytest


def test_usage_summary(client, auth_headers):
    """Authenticated user gets usage summary."""
    resp = client.get("/api/usage/summary", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "today_calls" in data
    assert "month_calls" in data
    assert "month_limit" in data
    assert "plan" in data
    assert data["plan"] == "pro"
    assert data["month_limit"] == 50000


def test_usage_summary_free_user(client, free_auth_headers):
    """Free user gets correct plan limit."""
    resp = client.get("/api/usage/summary", headers=free_auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["plan"] == "free"
    assert data["month_limit"] == 1000


def test_usage_summary_unauthenticated(client):
    """Unauthenticated request returns 401."""
    resp = client.get("/api/usage/summary")
    assert resp.status_code == 401


def test_usage_chart_7d(client, auth_headers):
    """Get 7-day chart data."""
    resp = client.get("/api/usage/chart?range=7d", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) == 7


def test_usage_chart_30d(client, auth_headers):
    """Get 30-day chart data."""
    resp = client.get("/api/usage/chart?range=30d", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 30


def test_usage_chart_90d(client, auth_headers):
    """Get 90-day chart data."""
    resp = client.get("/api/usage/chart?range=90d", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 90


def test_usage_chart_invalid_range(client, auth_headers):
    """Invalid chart range returns 422."""
    resp = client.get("/api/usage/chart?range=1y", headers=auth_headers)
    assert resp.status_code == 422


def test_usage_logs(client, auth_headers):
    """Get usage logs with pagination."""
    resp = client.get("/api/usage/logs?page=1", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert "total" in data
    assert "page" in data
    assert data["page"] == 1
    assert data["per_page"] == 20


def test_usage_logs_status_filter(client, auth_headers):
    """Filter logs by status class."""
    resp = client.get("/api/usage/logs?status=2xx", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    for item in data["items"]:
        assert 200 <= item["status_code"] < 300


def test_usage_logs_search(client, auth_headers):
    """Search logs by endpoint."""
    resp = client.get("/api/usage/logs?search=data", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    for item in data["items"]:
        assert "data" in item["endpoint"]
