from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select

from app.api.deps import DbSession, get_current_user, require_role
from app.core.config import settings
from app.core.limiting import limiter
from app.models.user import User, UserRole
from app.schemas.auth import AuthSessionResponse, LoginRequest, RefreshRequest, RegisterRequest, TokenPairResponse, UserResponse
from app.services.security import create_access_token, create_refresh_token, decode_token, hash_password, is_invalid_token_error, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register_user(payload: RegisterRequest, db: DbSession) -> User:
    existing_user = await db.scalar(select(User).where(User.email == payload.email))
    if existing_user is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    user = User(
        email=payload.email,
        hashed_password=hash_password(payload.password),
        role=payload.role,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@router.post("/login", response_model=AuthSessionResponse)
@limiter.limit(settings.login_rate_limit)
async def login_user(request: Request, response: Response, payload: LoginRequest, db: DbSession) -> AuthSessionResponse:
    user = await db.scalar(select(User).where(User.email == payload.email))
    if user is None or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

    tokens = TokenPairResponse(
        access_token=create_access_token(user.email, user.role.value),
        refresh_token=create_refresh_token(user.email, user.role.value),
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

    email = token_payload.get("sub")
    if not email:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token subject missing")

    user = await db.scalar(select(User).where(User.email == email))
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User no longer exists")

    return TokenPairResponse(
        access_token=create_access_token(user.email, user.role.value),
        refresh_token=create_refresh_token(user.email, user.role.value),
    )


@router.get("/me", response_model=UserResponse)
async def read_current_user(current_user: Annotated[User, Depends(get_current_user)]) -> User:
    return current_user


@router.get("/admin-check", response_model=dict[str, str])
async def admin_check(
    current_user: Annotated[User, Depends(require_role(UserRole.ADMIN))],
) -> dict[str, str]:
    return {"message": f"Admin access granted for {current_user.email}"}
