import uuid
from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.core import deps
from app.core.config import get_settings
from app.db.session import async_session_factory
from app.main import app
from app.models.organization import Organization
from app.models.user import User
from app.repositories.rbac import RBACRepository

_PROVIDER_KEY_SETTINGS = (
    "virustotal_api_key",
    "abuseipdb_api_key",
    "shodan_api_key",
    "otx_api_key",
    "greynoise_api_key",
    "abusech_api_key",
    "urlscan_api_key",
)


@pytest.fixture(autouse=True)
def _default_to_mock_providers(monkeypatch):
    """Tests must be deterministic regardless of what's actually configured
    in the developer's real .env — force every threat-intel provider key to
    unset by default so the Investigate module always exercises its mock
    providers here. A test that wants to exercise a real-provider code path
    (e.g. test_investigate_provider_health.py) re-enables just one key via
    its own fixture, layered on top of this."""
    settings = get_settings()
    for key_name in _PROVIDER_KEY_SETTINGS:
        monkeypatch.setattr(settings, key_name, None)


@pytest_asyncio.fixture
async def client() -> AsyncIterator[AsyncClient]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture
async def org_and_user() -> AsyncIterator[tuple[uuid.UUID, uuid.UUID]]:
    """Creates a fresh org + user per test, grants it the `admin` role (so
    every RBAC-guarded route passes its permission check), and overrides
    get_current_user so routes never need a real JWT in these tests.

    get_current_org_id/get_current_user_id both derive from
    get_current_user in app.core.deps, so overriding that one dependency
    is enough — no need to override them separately.
    """
    org_id = uuid.uuid4()
    user_id = uuid.uuid4()

    async with async_session_factory() as session:
        session.add(Organization(id=org_id, name=f"Test Org {org_id}"))
        session.add(
            User(
                id=user_id,
                org_id=org_id,
                email=f"{user_id}@test.sentris-dev.io",
                password_hash="test-placeholder",
                full_name="Test User",
            )
        )
        await session.commit()

        rbac_repo = RBACRepository(session)
        admin_role = await rbac_repo.get_role_by_name("admin")
        if admin_role is not None:
            await rbac_repo.assign_role(user_id, admin_role.id)
            await session.commit()

    async def _get_current_user() -> User:
        async with async_session_factory() as session:
            user = await session.get(User, user_id)
            assert user is not None
            return user

    app.dependency_overrides[deps.get_current_user] = _get_current_user
    yield org_id, user_id
    app.dependency_overrides.pop(deps.get_current_user, None)
