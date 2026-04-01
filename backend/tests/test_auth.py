"""Tests for auth endpoints."""
import pytest


def test_me_authenticated(client, auth_headers):
    """Authenticated user can get their info."""
    resp = client.get("/api/auth/me", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == "user_pro_001"
    assert data["username"] == "alice-dev"
    assert data["plan"] == "pro"


def test_me_unauthenticated(client):
    """Unauthenticated request returns 401."""
    resp = client.get("/api/auth/me")
    assert resp.status_code == 401


def test_me_invalid_token(client):
    """Invalid token returns 401."""
    resp = client.get("/api/auth/me", headers={"Authorization": "Bearer invalid"})
    assert resp.status_code == 401


def test_logout(client, auth_headers):
    """Logout clears session."""
    resp = client.post("/api/auth/logout", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["ok"] is True


def test_dev_login(client):
    """Dev login endpoint sets session cookie."""
    resp = client.get("/api/auth/dev-login?user_id=user_pro_001")
    assert resp.status_code == 200
    assert resp.json()["user_id"] == "user_pro_001"


def test_dev_login_nonexistent_user(client):
    """Dev login with non-existent user returns 404."""
    resp = client.get("/api/auth/dev-login?user_id=nonexistent")
    assert resp.status_code == 404


def test_login_redirects(client):
    """Login endpoint redirects to GitHub."""
    resp = client.get("/api/auth/login", follow_redirects=False)
    assert resp.status_code == 307
    assert "github.com" in resp.headers["location"]
