"""Tests for billing endpoints."""
import pytest


def test_current_plan(client, auth_headers):
    """Get current plan info."""
    resp = client.get("/api/billing/current", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["plan"] == "pro"
    assert data["plan_name"] == "Pro"
    assert data["limit"] == 50000


def test_current_plan_unauthenticated(client):
    """Unauthenticated request returns 401."""
    resp = client.get("/api/billing/current")
    assert resp.status_code == 401


def test_checkout_pro(client, free_auth_headers):
    """Free user can checkout for pro plan."""
    resp = client.post("/api/billing/checkout", headers=free_auth_headers, json={
        "plan": "pro",
        "billing_cycle": "monthly",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "checkout_url" in data
    assert "session_id" in data


def test_checkout_free_plan_fails(client, auth_headers):
    """Cannot checkout for free plan."""
    resp = client.post("/api/billing/checkout", headers=auth_headers, json={
        "plan": "free",
        "billing_cycle": "monthly",
    })
    assert resp.status_code == 400


def test_checkout_invalid_plan(client, auth_headers):
    """Invalid plan returns 400."""
    resp = client.post("/api/billing/checkout", headers=auth_headers, json={
        "plan": "ultra",
        "billing_cycle": "monthly",
    })
    assert resp.status_code == 400


def test_downgrade(client, auth_headers):
    """Pro user can downgrade to free."""
    resp = client.post("/api/billing/downgrade", headers=auth_headers, json={
        "plan": "free",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["new_plan"] == "free"


def test_downgrade_to_higher_plan_fails(client, free_auth_headers):
    """Cannot 'downgrade' to a higher plan."""
    resp = client.post("/api/billing/downgrade", headers=free_auth_headers, json={
        "plan": "pro",
    })
    assert resp.status_code == 400


def test_downgrade_invalid_plan(client, auth_headers):
    """Invalid plan returns 400."""
    resp = client.post("/api/billing/downgrade", headers=auth_headers, json={
        "plan": "nonexistent",
    })
    assert resp.status_code == 400


def test_invoices(client, auth_headers):
    """Get invoice list."""
    resp = client.get("/api/billing/invoices?page=1", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert "total" in data
    assert data["per_page"] == 10


def test_invoices_pagination(client, auth_headers):
    """Invoice pagination works."""
    resp = client.get("/api/billing/invoices?page=2", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["page"] == 2


def test_webhook_demo_mode(client):
    """Webhook in demo mode returns ok."""
    resp = client.post("/api/billing/webhook", content=b"test")
    assert resp.status_code == 200
    assert resp.json()["demo"] is True
