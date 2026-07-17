from datetime import UTC, datetime

from httpx import AsyncClient
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.db.session import async_session_factory
from app.models.mitre import MitreTechnique


async def _ensure_technique(technique_id: str, name: str, tactic: str) -> None:
    async with async_session_factory() as session:
        stmt = (
            pg_insert(MitreTechnique)
            .values(
                id=technique_id,
                name=name,
                tactic=tactic,
                description="test fixture technique",
                url=f"https://attack.mitre.org/techniques/{technique_id}/",
            )
            .on_conflict_do_nothing()
        )
        await session.execute(stmt)
        await session.commit()


async def test_create_alert_extracts_iocs_and_maps_mitre(
    client: AsyncClient, org_and_user
) -> None:
    await _ensure_technique("T1110", "Brute Force", "credential-access")

    create_resp = await client.post(
        "/api/v1/alerts",
        json={
            "source": "wazuh",
            "title": "Multiple failed logins followed by successful brute-force login",
            "raw": {"demo": True},
            "severity": "high",
            "rule_name": "ssh_brute_force_success",
            "src_ip": "198.51.100.23",
            "dst_ip": "10.0.1.5",
            "user_subject": "admin",
            "occurred_at": datetime.now(UTC).isoformat(),
        },
    )
    assert create_resp.status_code == 201
    alert_id = create_resp.json()["id"]

    detail_resp = await client.get(f"/api/v1/alerts/{alert_id}")
    assert detail_resp.status_code == 200
    detail = detail_resp.json()

    ioc_values = {ioc["value"] for ioc in detail["iocs"]}
    assert "198.51.100.23" in ioc_values
    assert "10.0.1.5" in ioc_values

    mitre_ids = {m["technique"]["id"] for m in detail["mitre"]}
    assert "T1110" in mitre_ids
    assert next(m for m in detail["mitre"] if m["technique"]["id"] == "T1110")["source"] == "rule"


async def test_list_alerts_filters_by_status_and_severity(
    client: AsyncClient, org_and_user
) -> None:
    await client.post(
        "/api/v1/alerts",
        json={
            "source": "sysmon",
            "title": "Benign process start",
            "raw": {},
            "severity": "low",
            "occurred_at": datetime.now(UTC).isoformat(),
        },
    )
    critical_resp = await client.post(
        "/api/v1/alerts",
        json={
            "source": "sysmon",
            "title": "Critical encoded PowerShell execution",
            "raw": {},
            "severity": "critical",
            "occurred_at": datetime.now(UTC).isoformat(),
        },
    )
    critical_id = critical_resp.json()["id"]

    filtered = await client.get("/api/v1/alerts", params={"severity": "critical"})
    assert filtered.status_code == 200
    page = filtered.json()
    assert page["total"] == 1
    assert page["items"][0]["id"] == critical_id


async def test_update_alert_status(client: AsyncClient, org_and_user) -> None:
    create_resp = await client.post(
        "/api/v1/alerts",
        json={
            "source": "suricata",
            "title": "Port scan detected",
            "raw": {},
            "occurred_at": datetime.now(UTC).isoformat(),
        },
    )
    alert_id = create_resp.json()["id"]

    patch_resp = await client.patch(f"/api/v1/alerts/{alert_id}", json={"status": "triaging"})
    assert patch_resp.status_code == 200
    assert patch_resp.json()["status"] == "triaging"
