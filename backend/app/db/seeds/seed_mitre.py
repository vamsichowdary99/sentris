"""Seeds the `mitre_techniques` reference table.

Run inside the API container: `make seed` (wraps `python -m app.db.seeds.seed_mitre`).

This ships a curated subset of well-known Enterprise ATT&CK techniques
spanning all 14 tactics — enough to drive the dashboard heatmap and AI
mapping demo. A full import from the official MITRE STIX/TAXII feed can
replace this later without changing the schema.
"""

import asyncio
import json
from pathlib import Path

from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.core.logging import configure_logging, get_logger
from app.db.session import async_session_factory
from app.models import MitreTechnique

SEED_FILE = Path(__file__).parent / "mitre_attack.json"


def _attack_url(technique_id: str) -> str:
    base = technique_id.split(".")[0]
    if "." in technique_id:
        sub = technique_id.split(".")[1]
        return f"https://attack.mitre.org/techniques/{base}/{sub}/"
    return f"https://attack.mitre.org/techniques/{base}/"


async def seed_mitre_techniques() -> int:
    techniques = json.loads(SEED_FILE.read_text())

    async with async_session_factory() as session:
        for technique in techniques:
            stmt = pg_insert(MitreTechnique).values(
                id=technique["id"],
                name=technique["name"],
                tactic=technique["tactic"],
                description=technique["description"],
                url=_attack_url(technique["id"]),
            )
            stmt = stmt.on_conflict_do_update(
                index_elements=["id"],
                set_={
                    "name": stmt.excluded.name,
                    "tactic": stmt.excluded.tactic,
                    "description": stmt.excluded.description,
                    "url": stmt.excluded.url,
                },
            )
            await session.execute(stmt)
        await session.commit()

    return len(techniques)


async def main() -> None:
    configure_logging()
    logger = get_logger(__name__)
    count = await seed_mitre_techniques()
    logger.info("seed.mitre_techniques.complete", count=count)


if __name__ == "__main__":
    asyncio.run(main())
