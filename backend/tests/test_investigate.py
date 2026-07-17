import asyncio
import json
from datetime import UTC, datetime

import pytest
from httpx import AsyncClient

from app.ai.router import AIRouter, LLMResponse, LLMUnavailableError
from app.core.config import get_settings
from app.integrations.base import EnrichmentResult
from app.integrations.mock_provider import MockShodanProvider

KNOWN_BAD_IP = "185.220.101.45"


def _fake_response(content: dict) -> LLMResponse:
    return LLMResponse(
        content=json.dumps(content),
        provider="test-provider",
        model="test-model",
        tokens_in=10,
        tokens_out=20,
        latency_ms=5,
    )


@pytest.fixture
def queued_ai_responses(monkeypatch):
    responses: list[LLMResponse] = []

    async def fake_complete(self, *, user, system=None, json_mode=False, max_tokens=900):
        if not responses:
            raise LLMUnavailableError("no fake response queued for this test")
        return responses.pop(0)

    monkeypatch.setattr(AIRouter, "complete", fake_complete)
    return responses


async def test_investigate_known_bad_ip_returns_multiple_providers_and_caches(
    client: AsyncClient, org_and_user
) -> None:
    resp = await client.post("/api/v1/investigate", json={"indicator": KNOWN_BAD_IP})
    assert resp.status_code == 200
    body = resp.json()

    assert body["detected_type"] == "ip"
    assert body["ioc"]["value"] == KNOWN_BAD_IP
    assert len(body["providers"]) >= 3
    assert all(p["status"] == "ok" for p in body["providers"])
    assert any(
        p["provider"] == "virustotal" and p["verdict"] == "malicious" for p in body["providers"]
    )

    ioc_id = body["ioc"]["id"]

    # Re-running immediately should hit the per-(ioc, provider) cache instead
    # of re-fetching from every source.
    rerun = await client.post("/api/v1/investigate", json={"indicator": KNOWN_BAD_IP})
    assert rerun.status_code == 200
    assert all(p["status"] == "cached" for p in rerun.json()["providers"])

    detail = await client.get(f"/api/v1/investigate/{ioc_id}")
    assert detail.status_code == 200
    assert len(detail.json()["providers"]) == len(body["providers"])


async def test_investigate_rejects_junk_input(client: AsyncClient, org_and_user) -> None:
    resp = await client.post("/api/v1/investigate", json={"indicator": "!! not an indicator !!"})
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "invalid_indicator"


async def test_investigate_provider_timeout_yields_partial_results(
    client: AsyncClient, org_and_user, monkeypatch
) -> None:
    settings = get_settings()
    monkeypatch.setattr(settings, "investigate_provider_timeout_seconds", 0.1)

    async def _slow_check(self, ioc_type, value):
        await asyncio.sleep(1.0)
        return EnrichmentResult(provider="shodan", verdict="clean", score=0.0, raw={})

    monkeypatch.setattr(MockShodanProvider, "check", _slow_check)

    resp = await client.post("/api/v1/investigate", json={"indicator": "203.0.113.44"})
    assert resp.status_code == 200
    providers = {p["provider"]: p["status"] for p in resp.json()["providers"]}

    assert providers["shodan"] == "timeout"
    # every other routed provider for an IP still completed despite shodan hanging
    assert providers["virustotal"] == "ok"
    assert providers["abuseipdb"] == "ok"
    assert providers["otx"] == "ok"
    assert providers["greynoise"] == "ok"


async def test_investigate_report_schema_validates(
    client: AsyncClient, org_and_user, queued_ai_responses
) -> None:
    queued_ai_responses.append(
        _fake_response(
            {
                "verdict": "malicious",
                "confidence": 0.92,
                "rationale": "Multiple sources confirm known C2 infrastructure.",
                "attribution": {
                    "malware_family": "Emotet",
                    "campaign": "SilentTrinity",
                    "threat_actor": "APT-Ghost",
                    "summary": "Linked to the SilentTrinity campaign via OTX pulses.",
                },
                "evidence": [
                    "VirusTotal: 14/90 engines flag this malicious",
                    "AbuseIPDB: 92% abuse confidence, 47 reports",
                ],
                "context": {
                    "geo": None,
                    "asn": None,
                    "first_seen": None,
                    "last_seen": None,
                    "scanner_classification": None,
                    "exposure": None,
                },
                "conflicts": [],
                "recommended_actions": [
                    {
                        "action": "Block at the perimeter firewall",
                        "rationale": "Confirmed malicious",
                    }
                ],
            }
        )
    )

    resp = await client.post("/api/v1/investigate/report", json={"indicator": KNOWN_BAD_IP})
    assert resp.status_code == 200
    body = resp.json()

    assert body["report"]["verdict"] == "malicious"
    assert body["report"]["attribution"]["malware_family"] == "Emotet"
    assert body["report"]["conflicts"] == []
    assert len(body["report"]["recommended_actions"]) == 1


async def test_investigate_detail_surfaces_related_alerts(
    client: AsyncClient, org_and_user
) -> None:
    await client.post(
        "/api/v1/alerts",
        json={
            "source": "wazuh",
            "title": "Brute force login attempt",
            "raw": {},
            "severity": "high",
            "src_ip": KNOWN_BAD_IP,
            "occurred_at": datetime.now(UTC).isoformat(),
        },
    )

    resp = await client.post("/api/v1/investigate", json={"indicator": KNOWN_BAD_IP})
    ioc_id = resp.json()["ioc"]["id"]

    detail = await client.get(f"/api/v1/investigate/{ioc_id}")
    assert detail.status_code == 200
    related_titles = {a["title"] for a in detail.json()["related_alerts"]}
    assert "Brute force login attempt" in related_titles
