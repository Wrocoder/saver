from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.schemas import (
    AuthLoginRequest,
    AuthRefreshRequest,
    AuthRegisterRequest,
    AuthResponse,
    AuthTokenResponse,
    UserResponse,
)
from app.db.models import UserProfileRecord, UserRecord
from app.db.session import get_db
from app.services.auth import (
    EmailAlreadyRegisteredError,
    InvalidCredentialsError,
    InvalidRefreshTokenError,
    authenticate_user,
    register_user,
    revoke_refresh_token,
    rotate_refresh_token,
)


router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def register(payload: AuthRegisterRequest, db: Session = Depends(get_db)) -> AuthResponse:
    try:
        user, access_token, refresh_token = register_user(
            db=db,
            email=payload.email,
            password=payload.password,
            name=payload.name,
            base_currency=payload.base_currency,
        )
    except EmailAlreadyRegisteredError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    return build_auth_response(db, user, access_token, refresh_token)


@router.post("/login", response_model=AuthResponse)
def login(payload: AuthLoginRequest, db: Session = Depends(get_db)) -> AuthResponse:
    try:
        user, access_token, refresh_token = authenticate_user(
            db=db,
            email=payload.email,
            password=payload.password,
        )
    except InvalidCredentialsError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc

    return build_auth_response(db, user, access_token, refresh_token)


@router.post("/refresh", response_model=AuthTokenResponse)
def refresh(payload: AuthRefreshRequest, db: Session = Depends(get_db)) -> AuthTokenResponse:
    try:
        _, access_token, refresh_token = rotate_refresh_token(db, payload.refresh_token)
    except InvalidRefreshTokenError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc

    return AuthTokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/logout")
def logout(payload: AuthRefreshRequest, db: Session = Depends(get_db)) -> dict[str, str]:
    revoke_refresh_token(db, payload.refresh_token)
    return {"status": "ok"}


def build_auth_response(
    db: Session,
    user: UserRecord,
    access_token: str,
    refresh_token: str,
) -> AuthResponse:
    profile = db.get(UserProfileRecord, user.id)
    return AuthResponse(
        user=UserResponse(
            id=user.id,
            email=user.email,
            name=profile.name if profile else None,
            base_currency=profile.base_currency if profile else "USD",
        ),
        access_token=access_token,
        refresh_token=refresh_token,
    )
