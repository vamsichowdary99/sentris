from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.demo_identity import DEMO_ORG_ID
from app.core.deps import get_current_user
from app.core.rate_limit import limiter
from app.db.session import get_db_session
from app.models.user import User
from app.schemas.auth import (
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenPairResponse,
    TokenRefreshResponse,
)
from app.schemas.user import UserMe, UserRead
from app.services.auth import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


def _client_ip(request: Request) -> str | None:
    return request.client.host if request.client else None


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
@limiter.limit("10/minute")
async def register(
    request: Request,
    data: RegisterRequest,
    db: AsyncSession = Depends(get_db_session),
) -> UserRead:
    # Demo/portfolio note: real multi-tenant signup (creating a fresh org
    # per registrant, or admin-gating registration entirely, per the
    # engineering plan) is out of scope here — every registrant joins the
    # single seeded demo org so the rest of the app stays single-tenant
    # for now.
    service = AuthService(db)
    user = await service.register(
        DEMO_ORG_ID, data, ip=_client_ip(request), user_agent=request.headers.get("user-agent")
    )
    return UserRead.model_validate(user)


@router.post("/login", response_model=TokenPairResponse)
@limiter.limit("5/minute")
async def login(
    request: Request, data: LoginRequest, db: AsyncSession = Depends(get_db_session)
) -> TokenPairResponse:
    service = AuthService(db)
    user, access_token, refresh_token = await service.authenticate(
        data, ip=_client_ip(request), user_agent=request.headers.get("user-agent")
    )
    return TokenPairResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=UserRead.model_validate(user),
    )


@router.post("/refresh", response_model=TokenRefreshResponse)
async def refresh(
    data: RefreshRequest, db: AsyncSession = Depends(get_db_session)
) -> TokenRefreshResponse:
    service = AuthService(db)
    access_token, new_refresh_token = await service.refresh(data.refresh_token)
    return TokenRefreshResponse(access_token=access_token, refresh_token=new_refresh_token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(data: RefreshRequest, db: AsyncSession = Depends(get_db_session)) -> None:
    service = AuthService(db)
    await service.logout(data.refresh_token)


@router.get("/me", response_model=UserMe)
async def me(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db_session)
) -> UserMe:
    service = AuthService(db)
    roles, permissions = await service.get_me(user)
    return UserMe(user=UserRead.model_validate(user), roles=roles, permissions=permissions)
