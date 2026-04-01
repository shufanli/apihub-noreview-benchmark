"""Tests for API keys endpoints."""
import pytest


def test_list_keys(client, auth_headers):
    """User can list their API keys."""
    resp = client.get("/api/keys", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) >= 2  # Pro user has 2 seed keys


def test_list_keys_unauthenticated(client):
    """Unauthenticated request returns 401."""
    resp = client.get("/api/keys")
    assert resp.status_code == 401


def test_create_key(client, auth_headers):
    """Create a new API key."""
    resp = client.post("/api/keys", headers=auth_headers, json={
        "name": "Test Key",
        "description": "For testing",
        "permissions": ["read", "write"],
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Test Key"
    assert "key" in data
    assert data["key"].startswith("ah_")
    assert "read" in data["permissions"]
    assert "write" in data["permissions"]


def test_create_key_empty_name(client, auth_headers):
    """Creating a key with empty name fails."""
    resp = client.post("/api/keys", headers=auth_headers, json={
        "name": "  ",
        "description": "",
        "permissions": ["read"],
    })
    assert resp.status_code == 400


def test_create_key_no_permissions(client, auth_headers):
    """Creating a key with no permissions fails."""
    resp = client.post("/api/keys", headers=auth_headers, json={
        "name": "Test Key",
        "permissions": [],
    })
    assert resp.status_code == 400


def test_create_key_invalid_permission(client, auth_headers):
    """Creating a key with invalid permission fails."""
    resp = client.post("/api/keys", headers=auth_headers, json={
        "name": "Test Key",
        "permissions": ["read", "superadmin"],
    })
    assert resp.status_code == 400


def test_delete_key(client, auth_headers):
    """User can delete their own key."""
    resp = client.delete("/api/keys/key_001", headers=auth_headers)
    assert resp.status_code == 200

    # Verify it's gone
    resp = client.get("/api/keys", headers=auth_headers)
    ids = [k["id"] for k in resp.json()]
    assert "key_001" not in ids


def test_delete_key_not_found(client, auth_headers):
    """Deleting non-existent key returns 404."""
    resp = client.delete("/api/keys/nonexistent", headers=auth_headers)
    assert resp.status_code == 404


def test_delete_other_users_key(client, free_auth_headers):
    """User cannot delete another user's key."""
    resp = client.delete("/api/keys/key_001", headers=free_auth_headers)
    assert resp.status_code == 404  # key_001 belongs to pro user
