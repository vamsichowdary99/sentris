"""Seeds the RBAC reference data: roles, permissions, and the mapping
between them. Run inside the API container:
`make seed-rbac` (or `python -m app.db.seeds.seed_rbac`). Idempotent.
"""

from __future__ import annotations

import asyncio

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.core.logging import configure_logging, get_logger
from app.db.session import async_session_factory
from app.models.rbac import Permission, Role, RolePermission

ROLES = ["admin", "soc_lead", "analyst", "viewer"]

PERMISSIONS = [
    "alert.read",
    "alert.write",
    "case.read",
    "case.write",
    "ioc.read",
    "ioc.write",
    "asset.read",
    "asset.write",
    "mitre.read",
    "metrics.read",
    "search.read",
    "audit.read",
    "user.manage",
    "integration.manage",
    "ai.use",
]

VIEWER_PERMISSIONS = [
    "alert.read",
    "case.read",
    "ioc.read",
    "asset.read",
    "mitre.read",
    "metrics.read",
    "search.read",
]
ANALYST_PERMISSIONS = [
    *VIEWER_PERMISSIONS,
    "alert.write",
    "case.write",
    "ioc.write",
    "asset.write",
    "ai.use",
]
SOC_LEAD_PERMISSIONS = [*ANALYST_PERMISSIONS, "audit.read"]
ADMIN_PERMISSIONS = [*SOC_LEAD_PERMISSIONS, "user.manage", "integration.manage"]

ROLE_PERMISSIONS: dict[str, list[str]] = {
    "viewer": VIEWER_PERMISSIONS,
    "analyst": ANALYST_PERMISSIONS,
    "soc_lead": SOC_LEAD_PERMISSIONS,
    "admin": ADMIN_PERMISSIONS,
}


async def seed_rbac() -> None:
    async with async_session_factory() as session:
        for name in ROLES:
            stmt = pg_insert(Role).values(name=name).on_conflict_do_nothing(index_elements=["name"])
            await session.execute(stmt)

        for code in PERMISSIONS:
            stmt = (
                pg_insert(Permission)
                .values(code=code)
                .on_conflict_do_nothing(index_elements=["code"])
            )
            await session.execute(stmt)
        await session.commit()

        roles_by_name = {
            r.name: r for r in (await session.execute(select(Role))).scalars().all()
        }
        permissions_by_code = {
            p.code: p for p in (await session.execute(select(Permission))).scalars().all()
        }

        for role_name, codes in ROLE_PERMISSIONS.items():
            role = roles_by_name[role_name]
            for code in codes:
                permission = permissions_by_code[code]
                stmt = (
                    pg_insert(RolePermission)
                    .values(role_id=role.id, permission_id=permission.id)
                    .on_conflict_do_nothing()
                )
                await session.execute(stmt)
        await session.commit()


async def main() -> None:
    configure_logging()
    logger = get_logger(__name__)
    await seed_rbac()
    logger.info("seed.rbac.complete", roles=len(ROLES), permissions=len(PERMISSIONS))


if __name__ == "__main__":
    asyncio.run(main())
