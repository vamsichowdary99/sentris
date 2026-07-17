from datetime import UTC, datetime

from httpx import AsyncClient


async def test_search_alerts_by_structured_filters(client: AsyncClient, org_and_user) -> None:
    await client.post(
        "/api/v1/alerts",
        json={
            "source": "wazuh",
            "title": "Searchable alert",
            "raw": {},
            "severity": "high",
            "occurred_at": datetime.now(UTC).isoformat(),
        },
    )

    resp = await client.post("/api/v1/search", json={"severity": "high"})
    assert resp.status_code == 200
    assert resp.json()["total"] == 1


async def test_saved_search_create_and_list(client: AsyncClient, org_and_user) -> None:
    create_resp = await client.post(
        "/api/v1/search/saved",
        json={"name": "Critical alerts", "query": {"severity": "critical"}},
    )
    assert create_resp.status_code == 201

    list_resp = await client.get("/api/v1/search/saved")
    assert list_resp.status_code == 200
    assert list_resp.json()[0]["name"] == "Critical alerts"
