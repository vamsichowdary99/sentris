import urllib.parse
from typing import Any

import httpx

from app.integrations.base import EnrichmentResult, ThreatIntelProvider
from app.integrations.http_helpers import raise_for_provider_errors
from app.models.enums import IOCType

_SECTIONS = {
    IOCType.ip: "IPv4",
    IOCType.domain: "domain",
    IOCType.hash: "file",
    IOCType.url: "url",
}


def _pulse_malware_families(pulse: dict[str, Any]) -> list[str]:
    """OTX pulses represent malware_families as a list of *objects*
    ({"display_name": ..., "id": ..., "target": ...}), not plain strings —
    normalize defensively since a bare string would also be valid input if
    OTX ever changes shape."""
    names = []
    for family in pulse.get("malware_families", []) or []:
        if isinstance(family, dict):
            name = family.get("display_name") or family.get("name")
            if name:
                names.append(name)
        elif isinstance(family, str) and family:
            names.append(family)
    return names


class OTXProvider(ThreatIntelProvider):
    """AlienVault OTX — https://otx.alienvault.com/assets/static/external_api.html
    Auth: `X-OTX-API-KEY` header. Attribution (campaigns/threat actors/pulses)."""

    name = "otx"
    supported_types = frozenset({IOCType.ip, IOCType.domain, IOCType.hash, IOCType.url})
    base_url = "https://otx.alienvault.com/api/v1/indicators"

    def __init__(self, api_key: str) -> None:
        self.api_key = api_key

    async def check(self, ioc_type: IOCType, value: str) -> EnrichmentResult:
        indicator = urllib.parse.quote(value, safe="") if ioc_type == IOCType.url else value
        url = f"{self.base_url}/{_SECTIONS[ioc_type]}/{indicator}/general"
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, headers={"X-OTX-API-KEY": self.api_key})

        if resp.status_code == 404:
            return EnrichmentResult(
                provider=self.name, verdict="unknown", score=None, raw={"found": False}
            )
        raise_for_provider_errors(resp)

        data = resp.json()
        pulse_info = data.get("pulse_info") or {}
        pulse_count = pulse_info.get("count") or 0
        pulses = pulse_info.get("pulses") or []

        malware_families = sorted({name for p in pulses for name in _pulse_malware_families(p)})
        adversaries = sorted({p["adversary"] for p in pulses if p.get("adversary")})

        verdict = "malicious" if pulse_count > 3 else "suspicious" if pulse_count > 0 else "clean"
        return EnrichmentResult(
            provider=self.name,
            verdict=verdict,
            score=float(min(pulse_count * 8, 100)),
            raw={
                "found": True,
                "pulse_count": pulse_count,
                "malware_families": malware_families,
                "adversary": adversaries[0] if adversaries else None,
                "campaign": pulses[0].get("name") if pulses else None,
            },
        )
