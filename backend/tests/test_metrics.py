from datetime import UTC, datetime

from httpx import AsyncClient


async def test_metrics_overview_reflects_seeded_alert(
    client: AsyncClient, org_and_user
) -> None:
    await client.post(
        "/api/v1/alerts",
        json={
            "source": "wazuh",
            "title": "Alert for metrics",
            "raw": {},
            "severity": "critical",
            "occurred_at": datetime.now(UTC).isoformat(),
        },
    )

    resp = await client.get("/api/v1/metrics/overview")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_alerts"] == 1
    assert body["alerts_by_severity"]["critical"] == 1


async def test_mttr_and_heatmap_endpoints_respond(client: AsyncClient, org_and_user) -> None:
    mttr_resp = await client.get("/api/v1/metrics/mttr")
    assert mttr_resp.status_code == 200
    assert mttr_resp.json()["sample_size"] == 0

    heatmap_resp = await client.get("/api/v1/metrics/mitre-heatmap")
    assert heatmap_resp.status_code == 200
    assert heatmap_resp.json() == []
