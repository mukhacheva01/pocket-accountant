"""Integration tests for the /api/tax endpoints."""

from tests.integration.conftest import make_test_settings


class TestTaxParseQueryEndpoint:
    def test_looks_like_calculation(self, app_client):
        resp = app_client.post("/api/tax/parse-query", json={
            "query": "посчитай усн 6 доход 500000",
            "profile": {"entity_type": "ip", "has_employees": False},
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["is_calculation"] is True

    def test_not_calculation(self, app_client):
        resp = app_client.post("/api/tax/parse-query", json={
            "query": "когда платить усн?",
            "profile": {},
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["is_calculation"] is False
