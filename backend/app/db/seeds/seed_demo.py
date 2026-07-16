"""Seeds a demo organization, user, assets, alerts, and a case so the API
is immediately explorable in Swagger and the Phase-3 frontend has
something to render. All data here is clearly synthetic — see the
`demo: true` marker in each alert's `raw` payload and the "Demo Org" name.

Demo login: demo@sentris.io / demo12345 (role: soc_lead). Run
`make seed-rbac` first so the role exists for assignment.

Run inside the API container: `make seed-demo` (or
`python -m app.db.seeds.seed_demo`). Idempotent: safe to re-run.
"""

import asyncio
from datetime import UTC, datetime

from app.core.demo_identity import DEMO_ORG_ID, DEMO_USER_ID
from app.core.logging import configure_logging, get_logger
from app.core.security import hash_password
from app.db.session import async_session_factory
from app.models.asset import Asset
from app.models.enums import AssetCriticality, Severity
from app.models.organization import Organization
from app.models.user import User
from app.repositories.asset import AssetRepository
from app.repositories.rbac import RBACRepository
from app.schemas.alert import AlertCreate
from app.schemas.case import CaseCreate
from app.services.alert import AlertService
from app.services.case import CaseService

DEMO_PASSWORD = "demo12345"  # noqa: S105 - portfolio demo credential, documented in README


async def seed_demo() -> None:
    async with async_session_factory() as session:
        org = await session.get(Organization, DEMO_ORG_ID)
        if org is None:
            session.add(Organization(id=DEMO_ORG_ID, name="Demo Org"))

        user = await session.get(User, DEMO_USER_ID)
        if user is None:
            user = User(
                id=DEMO_USER_ID,
                org_id=DEMO_ORG_ID,
                email="demo@sentris.io",
                password_hash=hash_password(DEMO_PASSWORD),
                full_name="Demo Analyst",
                is_active=True,
            )
            session.add(user)
        else:
            # Upgrading an existing dev DB from before Phase 4 (placeholder
            # password hash) or before the .local email fix (rejected by
            # email-validator as a reserved special-use domain).
            if user.password_hash == "pre-auth-placeholder-not-a-real-hash":
                user.password_hash = hash_password(DEMO_PASSWORD)
            if user.email == "demo@sentris.local":
                user.email = "demo@sentris.io"
        await session.commit()

        rbac_repo = RBACRepository(session)
        if not await rbac_repo.get_user_roles(DEMO_USER_ID):
            soc_lead = await rbac_repo.get_role_by_name("soc_lead")
            if soc_lead is not None:
                await rbac_repo.assign_role(DEMO_USER_ID, soc_lead.id)
                await session.commit()

        asset_repo = AssetRepository(session)
        web01: Asset | None = None
        dc01: Asset | None = None
        _, asset_count = await asset_repo.list_page(DEMO_ORG_ID, 0, 1)
        if asset_count == 0:
            web01 = await asset_repo.create(
                DEMO_ORG_ID,
                hostname="web-01.demo.local",
                ip="10.0.1.10",
                os="Ubuntu 22.04",
                owner="platform-team",
                criticality=AssetCriticality.high,
            )
            dc01 = await asset_repo.create(
                DEMO_ORG_ID,
                hostname="dc-01.demo.local",
                ip="10.0.1.5",
                os="Windows Server 2022",
                owner="it-team",
                criticality=AssetCriticality.critical,
            )
            await session.commit()

        alert_service = AlertService(session)
        _, alert_count = await alert_service.list_page(DEMO_ORG_ID, 0, 1)
        if alert_count == 0:
            alert1 = await alert_service.create(
                DEMO_ORG_ID,
                AlertCreate(
                    source="wazuh",
                    external_id="wazuh-1001",
                    title="Multiple failed logins followed by successful brute-force login",
                    raw={"demo": True, "rule_id": 5716, "notes": "simulated for portfolio demo"},
                    severity=Severity.high,
                    rule_name="ssh_brute_force_success",
                    src_ip="198.51.100.23",
                    dst_ip="10.0.1.5",
                    host_asset_id=dc01.id if dc01 else None,
                    user_subject="admin",
                    occurred_at=datetime.now(UTC),
                ),
            )
            alert2 = await alert_service.create(
                DEMO_ORG_ID,
                AlertCreate(
                    source="sysmon",
                    external_id="sysmon-2044",
                    title="Suspicious PowerShell encoded command execution",
                    raw={"demo": True, "event_id": 1, "notes": "simulated for portfolio demo"},
                    severity=Severity.critical,
                    rule_name="powershell_encoded_command",
                    src_ip="10.0.1.10",
                    host_asset_id=web01.id if web01 else None,
                    user_subject="svc-web",
                    occurred_at=datetime.now(UTC),
                ),
            )

            case_service = CaseService(session)
            await case_service.create(
                DEMO_ORG_ID,
                DEMO_USER_ID,
                CaseCreate(
                    title="Suspected credential compromise on dc-01",
                    summary=(
                        "Brute-force login success on dc-01 followed by suspicious "
                        "PowerShell activity on web-01 — possible lateral movement."
                    ),
                    severity=Severity.critical,
                    alert_ids=[alert1.id, alert2.id],
                ),
            )


async def main() -> None:
    configure_logging()
    logger = get_logger(__name__)
    await seed_demo()
    logger.info("seed.demo.complete")


if __name__ == "__main__":
    asyncio.run(main())
