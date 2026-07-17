"""Provider-level tests against fixture payloads shaped to match the real,
currently-documented API schemas (VirusTotal v3, AbuseIPDB v2, AlienVault
OTX, GreyNoise Community v3) rather than the mock provider's shapes —
these exercise the real HTTP-parsing code path with httpx.AsyncClient.get
monkeypatched, so no live network call or real API key is needed while
still catching schema drift (e.g. OTX's malware_families being a list of
objects, not plain strings)."""

import httpx
import pytest

from app.integrations.abuseipdb import AbuseIPDBProvider
from app.integrations.greynoise import GreyNoiseProvider
from app.integrations.http_helpers import ProviderAuthError, ProviderRateLimitError
from app.integrations.otx import OTXProvider
from app.integrations.virustotal import VirusTotalProvider
from app.models.enums import IOCType


class FakeResponse:
    def __init__(self, status_code: int, json_data: dict | None = None, headers=None) -> None:
        self.status_code = status_code
        self._json_data = json_data or {}
        self.headers = headers or {}

    def json(self) -> dict:
        return self._json_data

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise httpx.HTTPStatusError(
                f"HTTP {self.status_code}", request=None, response=None  # type: ignore[arg-type]
            )


@pytest.fixture
def fake_http(monkeypatch):
    responses: dict[str, FakeResponse] = {}

    async def fake_get(self, url, params=None, headers=None):  # noqa: ANN001
        for pattern, resp in responses.items():
            if pattern in url:
                return resp
        raise AssertionError(f"no fake response registered for GET {url}")

    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)
    return responses


VT_MALICIOUS_IP = {
    "data": {
        "id": "185.220.101.45",
        "type": "ip_address",
        "attributes": {
            "reputation": -42,
            "country": "DE",
            "asn": 208294,
            "as_owner": "Bulletproof Hosting LLC",
            "last_analysis_stats": {
                "malicious": 14,
                "suspicious": 3,
                "undetected": 5,
                "harmless": 68,
                "timeout": 0,
            },
        },
    }
}

ABUSEIPDB_RESPONSE = {
    "data": {
        "ipAddress": "185.220.101.45",
        "isPublic": True,
        "abuseConfidenceScore": 100,
        "countryCode": "DE",
        "isp": "Bulletproof Hosting LLC",
        "isTor": True,
        "totalReports": 341,
        "lastReportedAt": "2026-07-10T12:00:00+00:00",
    }
}

OTX_GENERAL_WITH_OBJECT_MALWARE_FAMILIES = {
    "pulse_info": {
        "count": 12,
        "pulses": [
            {
                "id": "abc123",
                "name": "SilentTrinity C2 Infrastructure",
                "adversary": "APT-Ghost",
                # Real OTX shape: a list of objects, not plain strings.
                "malware_families": [{"display_name": "Emotet", "id": 55, "target": "malware"}],
                "tags": ["c2", "botnet"],
            }
        ],
    }
}

GREYNOISE_BENIGN_SCANNER = {
    "ip": "194.165.16.71",
    "noise": True,
    "riot": False,
    "classification": "benign",
    "name": "unknown",
    "last_seen": "2026-07-15",
    "message": "Success",
}


async def test_virustotal_parses_real_schema_malicious(fake_http) -> None:
    fake_http["virustotal.com"] = FakeResponse(200, VT_MALICIOUS_IP)
    result = await VirusTotalProvider("test-key").check(IOCType.ip, "185.220.101.45")
    assert result.verdict == "malicious"
    assert result.raw["last_analysis_stats"]["malicious"] == 14
    assert result.raw["as_owner"] == "Bulletproof Hosting LLC"


async def test_virustotal_404_is_valid_not_found(fake_http) -> None:
    fake_http["virustotal.com"] = FakeResponse(404)
    result = await VirusTotalProvider("test-key").check(IOCType.ip, "8.8.8.8")
    assert result.verdict == "unknown"
    assert result.raw == {"found": False}


async def test_virustotal_401_raises_auth_error(fake_http) -> None:
    fake_http["virustotal.com"] = FakeResponse(401)
    with pytest.raises(ProviderAuthError):
        await VirusTotalProvider("bad-key").check(IOCType.ip, "8.8.8.8")


async def test_virustotal_429_raises_rate_limit_with_retry_after(fake_http) -> None:
    fake_http["virustotal.com"] = FakeResponse(429, headers={"Retry-After": "30"})
    with pytest.raises(ProviderRateLimitError) as exc_info:
        await VirusTotalProvider("test-key").check(IOCType.ip, "8.8.8.8")
    assert exc_info.value.retry_after == 30.0


async def test_abuseipdb_parses_real_schema(fake_http) -> None:
    fake_http["abuseipdb.com"] = FakeResponse(200, ABUSEIPDB_RESPONSE)
    result = await AbuseIPDBProvider("test-key").check(IOCType.ip, "185.220.101.45")
    assert result.verdict == "malicious"
    assert result.raw["totalReports"] == 341
    assert result.raw["isTor"] is True


async def test_otx_parses_object_shaped_malware_families(fake_http) -> None:
    fake_http["otx.alienvault.com"] = FakeResponse(200, OTX_GENERAL_WITH_OBJECT_MALWARE_FAMILIES)
    result = await OTXProvider("test-key").check(IOCType.ip, "185.220.101.45")
    assert result.raw["malware_families"] == ["Emotet"]
    assert result.raw["adversary"] == "APT-Ghost"
    assert result.raw["campaign"] == "SilentTrinity C2 Infrastructure"
    assert result.verdict == "malicious"


async def test_otx_404_is_valid_not_found(fake_http) -> None:
    fake_http["otx.alienvault.com"] = FakeResponse(404)
    result = await OTXProvider("test-key").check(IOCType.domain, "example.com")
    assert result.verdict == "unknown"
    assert result.raw == {"found": False}


async def test_greynoise_classifies_benign_scanner(fake_http) -> None:
    fake_http["greynoise.io"] = FakeResponse(200, GREYNOISE_BENIGN_SCANNER)
    result = await GreyNoiseProvider("test-key").check(IOCType.ip, "194.165.16.71")
    assert result.verdict == "clean"
    assert result.raw["classification"] == "benign"
    assert result.raw["noise"] is True


async def test_greynoise_404_is_valid_no_data(fake_http) -> None:
    fake_http["greynoise.io"] = FakeResponse(404)
    result = await GreyNoiseProvider("test-key").check(IOCType.ip, "8.8.8.8")
    assert result.verdict == "unknown"
    assert result.raw["seen"] is False
