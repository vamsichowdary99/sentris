import asyncio
from typing import Any

import httpx

from app.integrations.base import EnrichmentResult, ThreatIntelProvider
from app.integrations.http_helpers import raise_for_provider_errors
from app.models.enums import IOCType


class UrlscanProvider(ThreatIntelProvider):
    """urlscan.io — https://urlscan.io/docs/api/
    Auth: `API-Key` header (not x-api-key). Genuinely async: submit a scan,
    then poll the result endpoint (which 404s until the scan finishes).
    Free-tier scans typically take 10-20s, longer than we can block a
    single request for — so this does a short bounded poll and, if the
    scan isn't done yet, returns a "scanning" result rather than blocking
    or timing out. InvestigateService._fan_out skips the cache-TTL check
    for a "scanning" outcome, so re-running the investigation polls the
    same scan forward instead of submitting a new one each time.
    """

    name = "urlscan"
    supported_types = frozenset({IOCType.domain, IOCType.url})
    submit_url = "https://urlscan.io/api/v1/scan/"
    result_url = "https://urlscan.io/api/v1/result"

    # Kept comfortably under InvestigateService's per-provider timeout
    # (default 12s) so this provider always gets to return its own
    # "scanning" result rather than being cut off as a generic timeout.
    poll_attempts = 3
    poll_interval_seconds = 2.5

    def __init__(self, api_key: str) -> None:
        self.api_key = api_key

    async def check(self, ioc_type: IOCType, value: str) -> EnrichmentResult:
        target_url = value if ioc_type == IOCType.url else f"https://{value}"

        async with httpx.AsyncClient(timeout=10.0) as client:
            submit_resp = await client.post(
                self.submit_url,
                json={"url": target_url, "visibility": "public"},
                headers={"API-Key": self.api_key, "Content-Type": "application/json"},
            )
            raise_for_provider_errors(submit_resp)
            scan_uuid = submit_resp.json()["uuid"]

            for _ in range(self.poll_attempts):
                await asyncio.sleep(self.poll_interval_seconds)
                result_resp = await client.get(
                    f"{self.result_url}/{scan_uuid}/", headers={"API-Key": self.api_key}
                )
                if result_resp.status_code == 404:
                    continue  # not ready yet
                raise_for_provider_errors(result_resp)
                return self._parse_result(scan_uuid, result_resp.json())

        return EnrichmentResult(
            provider=self.name,
            verdict="unknown",
            score=None,
            raw={
                "scan_status": "in_progress",
                "uuid": scan_uuid,
                "message": "Scan submitted — check back in a few seconds.",
            },
        )

    def _parse_result(self, scan_uuid: str, data: dict[str, Any]) -> EnrichmentResult:
        task = data.get("task") or {}
        page = data.get("page") or {}
        overall = (data.get("verdicts") or {}).get("overall") or {}

        malicious = bool(overall.get("malicious"))
        score = overall.get("score")
        return EnrichmentResult(
            provider=self.name,
            verdict="malicious" if malicious else "unknown",
            score=float(score) if isinstance(score, (int, float)) else None,
            raw={
                "scan_status": "complete",
                "uuid": scan_uuid,
                "screenshot_url": task.get("screenshotURL"),
                "report_url": task.get("reportURL"),
                "domain": page.get("domain"),
                "ip": page.get("ip"),
                "server": page.get("server"),
                "country": page.get("country"),
            },
        )
