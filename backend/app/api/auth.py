from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.api.deps import DbSession, get_current_user, require_role
from app.core.config import settings
from app.models.organization import Organization
from app.core.limiting import limiter
from app.models.user import User, UserRole
from app.schemas.auth import AuthSessionResponse, CreateTeammateRequest, LoginRequest, RefreshRequest, RegisterRequest, TokenPairResponse, UserResponse
from app.services.security import create_access_token, create_refresh_token, decode_token, hash_password, is_invalid_token_error, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register_user(payload: RegisterRequest, db: DbSession) -> User:
    existing_user = await db.scalar(select(User).where(User.email == payload.email))
    if existing_user is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    existing_organization = await db.scalar(select(Organization).where(Organization.name == payload.organization_name))
    if existing_organization is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Organization name already exists")

    organization = Organization(name=payload.organization_name)
    db.add(organization)
    await db.flush()

    user = User(
        email=payload.email,
        hashed_password=hash_password(payload.password),
        organization_id=organization.id,
        role=payload.role,
    )
    db.add(user)
    await db.commit()
    created_user = await db.scalar(
        select(User)
        .options(selectinload(User.organization))
        .where(User.email == payload.email)
    )
    if created_user is None:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to load created user")
    return created_user


@router.post("/login", response_model=AuthSessionResponse)
@limiter.limit(settings.login_rate_limit)
async def login_user(request: Request, response: Response, payload: LoginRequest, db: DbSession) -> AuthSessionResponse:
    user = await db.scalar(
        select(User)
        .options(selectinload(User.organization))
        .where(User.email == payload.email)
    )
    if user is None or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

    tokens = TokenPairResponse(
        access_token=create_access_token(user.id, user.role.value, user.organization_id),
        refresh_token=create_refresh_token(user.id, user.role.value, user.organization_id),
    )
    return AuthSessionResponse(user=user, tokens=tokens)


@router.post("/refresh", response_model=TokenPairResponse)
async def refresh_session(payload: RefreshRequest, db: DbSession) -> TokenPairResponse:
    try:
        token_payload = decode_token(payload.refresh_token)
    except Exception as error:
        if is_invalid_token_error(error):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired refresh token") from error
        raise

    if token_payload.get("type") != "refresh":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token required")

    subject = token_payload.get("sub")
    if not subject:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token subject missing")

    try:
        user_id = int(subject)
    except (TypeError, ValueError) as error:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token subject is invalid") from error

    user = await db.scalar(
        select(User)
        .options(selectinload(User.organization))
        .where(User.id == user_id)
    )
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User no longer exists")

    return TokenPairResponse(
        access_token=create_access_token(user.id, user.role.value, user.organization_id),
        refresh_token=create_refresh_token(user.id, user.role.value, user.organization_id),
    )


@router.get("/me", response_model=UserResponse)
async def read_current_user(current_user: Annotated[User, Depends(get_current_user)]) -> User:
    return current_user


@router.get("/admin-check", response_model=dict[str, str])
async def admin_check(
    current_user: Annotated[User, Depends(require_role(UserRole.ADMIN))],
) -> dict[str, str]:
    return {"message": f"Admin access granted for {current_user.email}"}


@router.post("/teammates", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_teammate(
    payload: CreateTeammateRequest,
    db: DbSession,
    current_user: Annotated[User, Depends(require_role(UserRole.ADMIN))],
) -> User:
    existing_user = await db.scalar(select(User).where(User.email == payload.email))
    if existing_user is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    teammate = User(
        email=payload.email,
        hashed_password=hash_password(payload.password),
        organization_id=current_user.organization_id,
        role=payload.role,
    )
    db.add(teammate)
    await db.commit()

    created_teammate = await db.scalar(
        select(User)
        .options(selectinload(User.organization))
        .where(User.email == payload.email)
    )
    if created_teammate is None:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to load created teammate")
    return created_teammate
