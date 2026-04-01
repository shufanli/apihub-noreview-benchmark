"""Tests for health endpoint."""


def test_health(client):
    """Health check returns ok."""
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"
