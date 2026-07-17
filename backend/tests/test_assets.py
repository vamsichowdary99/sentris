from httpx import AsyncClient


async def test_create_list_get_update_asset(client: AsyncClient, org_and_user) -> None:
    create_resp = await client.post(
        "/api/v1/assets",
        json={"hostname": "srv-01.test.local", "ip": "10.1.1.1", "criticality": "high"},
    )
    assert create_resp.status_code == 201
    asset = create_resp.json()
    assert asset["hostname"] == "srv-01.test.local"
    assert asset["criticality"] == "high"

    list_resp = await client.get("/api/v1/assets")
    assert list_resp.status_code == 200
    page = list_resp.json()
    assert page["total"] == 1
    assert page["items"][0]["id"] == asset["id"]

    get_resp = await client.get(f"/api/v1/assets/{asset['id']}")
    assert get_resp.status_code == 200
    assert get_resp.json()["hostname"] == "srv-01.test.local"

    patch_resp = await client.patch(
        f"/api/v1/assets/{asset['id']}", json={"criticality": "critical"}
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["criticality"] == "critical"


async def test_get_missing_asset_returns_404(client: AsyncClient, org_and_user) -> None:
    resp = await client.get("/api/v1/assets/00000000-0000-0000-0000-000000000099")
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "not_found"
