from datetime import UTC, datetime

from httpx import AsyncClient

from app.db.session import async_session_factory
from app.repositories.ioc import IOCRepository
from app.services.enrichment import EnrichmentService

# Curated in app.integrations.mock_provider.KNOWN_MALICIOUS — always resolves
# to a "malicious" verdict from the mock provider.
KNOWN_BAD_IP = "185.220.101.45"


async def test_enrich_ioc_creates_verdicts_from_mock_providers(
    client: AsyncClient, org_and_user
) -> None:
    org_id, _ = org_and_user

    async with async_session_factory() as session:
        ioc_repo = IOCRepository(session)
        ioc = await ioc_repo.get_or_create(org_id, type="ip", value=KNOWN_BAD_IP)
        await session.commit()

        enrichments = await EnrichmentService(session).enrich_ioc(ioc)

        providers = {e.provider for e in enrichments}
        assert providers == {"virustotal", "abuseipdb"}
        assert all(e.verdict == "malicious" for e in enrichments)
        assert ioc.reputation == "malicious"


async def test_force_enrich_endpoint_populates_alert_iocs(
    client: AsyncClient, org_and_user
) -> None:
    create_resp = await client.post(
        "/api/v1/alerts",
        json={
            "source": "wazuh",
            "title": "Suspicious inbound connection",
            "raw": {},
            "severity": "high",
            "src_ip": KNOWN_BAD_IP,
            "dst_ip": "10.0.0.9",
            "occurred_at": datetime.now(UTC).isoformat(),
        },
    )
    assert create_resp.status_code == 201
    alert_id = create_resp.json()["id"]

    enrich_resp = await client.post(f"/api/v1/alerts/{alert_id}/enrich")
    assert enrich_resp.status_code == 200
    detail = enrich_resp.json()

    bad_ioc = next(ioc for ioc in detail["iocs"] if ioc["value"] == KNOWN_BAD_IP)
    assert bad_ioc["reputation"] == "malicious"
    providers = {e["provider"] for e in bad_ioc["enrichments"]}
    assert providers == {"virustotal", "abuseipdb"}
