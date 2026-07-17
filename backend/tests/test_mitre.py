from httpx import AsyncClient
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.db.session import async_session_factory
from app.models.mitre import MitreTechnique


async def _ensure_technique(technique_id: str, tactic: str) -> None:
    async with async_session_factory() as session:
        stmt = (
            pg_insert(MitreTechnique)
            .values(
                id=technique_id,
                name=f"Technique {technique_id}",
                tactic=tactic,
                description="test fixture technique",
                url=f"https://attack.mitre.org/techniques/{technique_id}/",
            )
            .on_conflict_do_nothing()
        )
        await session.execute(stmt)
        await session.commit()


async def test_get_technique_by_id(client: AsyncClient, org_and_user) -> None:
    await _ensure_technique("T9001", "discovery")

    resp = await client.get("/api/v1/mitre/techniques/T9001")
    assert resp.status_code == 200
    assert resp.json()["tactic"] == "discovery"


async def test_get_missing_technique_returns_404(client: AsyncClient, org_and_user) -> None:
    resp = await client.get("/api/v1/mitre/techniques/T0000")
    assert resp.status_code == 404


async def test_list_techniques_filters_by_tactic(client: AsyncClient, org_and_user) -> None:
    await _ensure_technique("T9002", "impact")

    resp = await client.get("/api/v1/mitre/techniques", params={"tactic": "impact", "size": 200})
    assert resp.status_code == 200
    tactics = {t["tactic"] for t in resp.json()["items"]}
    assert tactics == {"impact"}
