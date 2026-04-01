"""Tests for pricing endpoint."""


def test_get_pricing(client):
    """Public pricing endpoint returns all plans."""
    resp = client.get("/api/pricing")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 3
    plan_ids = [p["id"] for p in data]
    assert "free" in plan_ids
    assert "pro" in plan_ids
    assert "enterprise" in plan_ids


def test_pricing_pro_is_popular(client):
    """Pro plan is marked as popular."""
    resp = client.get("/api/pricing")
    data = resp.json()
    pro = next(p for p in data if p["id"] == "pro")
    assert pro["popular"] is True


def test_pricing_has_features(client):
    """Each plan has features list."""
    resp = client.get("/api/pricing")
    data = resp.json()
    for plan in data:
        assert isinstance(plan["features"], list)
        assert len(plan["features"]) > 0


def test_pricing_yearly_discount(client):
    """Yearly price is less than monthly."""
    resp = client.get("/api/pricing")
    data = resp.json()
    pro = next(p for p in data if p["id"] == "pro")
    assert pro["price_yearly"] < pro["price_monthly"]
