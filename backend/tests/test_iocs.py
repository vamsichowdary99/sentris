from httpx import AsyncClient


async def test_create_and_get_ioc_with_enrichments(client: AsyncClient, org_and_user) -> None:
    create_resp = await client.post(
        "/api/v1/iocs", json={"type": "ip", "value": "203.0.113.7", "source": "manual"}
    )
    assert create_resp.status_code == 201
    ioc = create_resp.json()
    assert ioc["value"] == "203.0.113.7"

    get_resp = await client.get(f"/api/v1/iocs/{ioc['id']}")
    assert get_resp.status_code == 200
    detail = get_resp.json()
    assert detail["enrichments"] == []


async def test_create_ioc_is_deduplicated_per_org(client: AsyncClient, org_and_user) -> None:
    first = await client.post("/api/v1/iocs", json={"type": "domain", "value": "evil.example"})
    second = await client.post("/api/v1/iocs", json={"type": "domain", "value": "evil.example"})
    assert first.json()["id"] == second.json()["id"]

    list_resp = await client.get("/api/v1/iocs")
    assert list_resp.json()["total"] == 1
