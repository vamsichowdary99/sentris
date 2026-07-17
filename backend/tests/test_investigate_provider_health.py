"""Service-level tests for the rate-limiter/backoff and misconfigured-key
handling wired into InvestigateService._fan_out. These enable a real (not
mock) provider by monkeypatching settings, so the actual health-tracking
code path runs — the mock providers routed alongside it prove other
sources are unaffected by one provider being throttled/misconfigured.
"""

import httpx
import pytest
from httpx import AsyncClient

from app.core.config import get_settings
from app.integrations.provider_health import get_provider_health
from tests.test_investigate_providers import FakeResponse


@pytest.fixture(autouse=True)
async def clean_provider_health():
    health = get_provider_health()
    client = await health._client()
    keys = await client.keys("ratelimit:*") + await client.keys("integration:status:*")
    if keys:
        await client.delete(*keys)
    yield
    keys = await client.keys("ratelimit:*") + await client.keys("integration:status:*")
    if keys:
        await client.delete(*keys)


@pytest.fixture
def live_virustotal(monkeypatch):
    """Layered on top of conftest's autouse mock-everything fixture — just
    re-enables VirusTotal so this test can exercise the real-provider code
    path while every other provider stays deterministically mocked."""
    monkeypatch.setattr(get_settings(), "virustotal_api_key", "test-key")


async def test_misconfigured_provider_reported_via_401(
    client: AsyncClient, org_and_user, live_virustotal, monkeypatch
) -> None:
    original_get = httpx.AsyncClient.get

    async def fake_get(self, url, params=None, headers=None):  # noqa: ANN001
        if "virustotal.com" in str(url):
            return FakeResponse(401)
        # Anything else (including the test client's own calls into the
        # local ASGI app, which also go through httpx.AsyncClient.get)
        # falls through to the real implementation.
        return await original_get(self, url, params=params, headers=headers)

    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)

    resp = await client.post("/api/v1/investigate", json={"indicator": "8.8.8.8"})
    assert resp.status_code == 200
    providers = {p["provider"]: p["status"] for p in resp.json()["providers"]}
    assert providers["virustotal"] == "misconfigured"
    # other IP-routed providers stayed on their own (mocked) path, unaffected
    assert providers["abuseipdb"] == "ok"

    statuses = await client.get("/api/v1/integrations/status")
    vt_status = next(s for s in statuses.json() if s["provider"] == "virustotal")
    assert vt_status["last_status"] == "misconfigured"


async def test_rate_limit_backoff_blocks_second_call_without_hitting_http(
    client: AsyncClient, org_and_user, live_virustotal, monkeypatch
) -> None:
    call_count = 0
    original_get = httpx.AsyncClient.get

    async def fake_get(self, url, params=None, headers=None):  # noqa: ANN001
        nonlocal call_count
        if "virustotal.com" in str(url):
            call_count += 1
            return FakeResponse(429, headers={"Retry-After": "120"})
        return await original_get(self, url, params=params, headers=headers)

    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)

    first = await client.post("/api/v1/investigate", json={"indicator": "8.8.8.8"})
    assert first.status_code == 200
    ioc_id = first.json()["ioc"]["id"]
    first_providers = {p["provider"]: p["status"] for p in first.json()["providers"]}
    assert first_providers["virustotal"] == "rate_limited"
    assert call_count == 1

    # force_refresh bypasses the result cache, but the cooldown from the
    # 429 above must still block a second real HTTP call.
    second = await client.post(f"/api/v1/investigate/{ioc_id}/refresh")
    assert second.status_code == 200
    second_providers = {p["provider"]: p["status"] for p in second.json()["providers"]}
    assert second_providers["virustotal"] == "rate_limited"
    assert call_count == 1
