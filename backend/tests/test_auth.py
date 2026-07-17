import uuid

from httpx import AsyncClient


async def _register_and_login(client: AsyncClient) -> dict:
    email = f"{uuid.uuid4()}@test.sentris-dev.io"
    password = "correct-horse-battery-staple"

    register_resp = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "full_name": "Test Analyst"},
    )
    assert register_resp.status_code == 201

    login_resp = await client.post(
        "/api/v1/auth/login", json={"email": email, "password": password}
    )
    assert login_resp.status_code == 200
    return login_resp.json()


async def test_register_and_login(client: AsyncClient) -> None:
    tokens = await _register_and_login(client)
    assert tokens["access_token"]
    assert tokens["refresh_token"]
    assert tokens["user"]["email"]


async def test_login_with_wrong_password_is_rejected(client: AsyncClient) -> None:
    email = f"{uuid.uuid4()}@test.sentris-dev.io"
    await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "correct-horse-battery-staple", "full_name": "Test"},
    )
    resp = await client.post(
        "/api/v1/auth/login", json={"email": email, "password": "wrong-password"}
    )
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "unauthorized"


async def test_duplicate_registration_is_rejected(client: AsyncClient) -> None:
    email = f"{uuid.uuid4()}@test.sentris-dev.io"
    payload = {"email": email, "password": "correct-horse-battery-staple", "full_name": "Test"}
    first = await client.post("/api/v1/auth/register", json=payload)
    assert first.status_code == 201
    second = await client.post("/api/v1/auth/register", json=payload)
    assert second.status_code == 409


async def test_me_returns_default_analyst_role_and_permissions(client: AsyncClient) -> None:
    tokens = await _register_and_login(client)
    resp = await client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {tokens['access_token']}"}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["roles"] == ["analyst"]
    assert "alert.read" in body["permissions"]
    assert "alert.write" in body["permissions"]
    assert "audit.read" not in body["permissions"]


async def test_protected_route_rejects_missing_token(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/alerts")
    assert resp.status_code == 401


async def test_protected_route_rejects_garbage_token(client: AsyncClient) -> None:
    resp = await client.get(
        "/api/v1/alerts", headers={"Authorization": "Bearer not-a-real-token"}
    )
    assert resp.status_code == 401


async def test_default_analyst_role_cannot_read_audit_logs(client: AsyncClient) -> None:
    tokens = await _register_and_login(client)
    resp = await client.get(
        "/api/v1/audit-logs", headers={"Authorization": f"Bearer {tokens['access_token']}"}
    )
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "forbidden"


async def test_analyst_can_read_and_write_alerts(client: AsyncClient) -> None:
    tokens = await _register_and_login(client)
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    list_resp = await client.get("/api/v1/alerts", headers=headers)
    assert list_resp.status_code == 200


async def test_refresh_rotates_token_and_invalidates_old_one(client: AsyncClient) -> None:
    tokens = await _register_and_login(client)

    refresh_resp = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
    )
    assert refresh_resp.status_code == 200
    new_tokens = refresh_resp.json()
    assert new_tokens["refresh_token"] != tokens["refresh_token"]

    replay_resp = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
    )
    assert replay_resp.status_code == 401


async def test_logout_revokes_refresh_token(client: AsyncClient) -> None:
    tokens = await _register_and_login(client)

    logout_resp = await client.post(
        "/api/v1/auth/logout", json={"refresh_token": tokens["refresh_token"]}
    )
    assert logout_resp.status_code == 204

    refresh_resp = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
    )
    assert refresh_resp.status_code == 401
