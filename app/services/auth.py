from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import (
    create_access_token,
    create_refresh_token_value,
    hash_password,
    hash_refresh_token,
    refresh_token_expiry,
    verify_password,
)
from app.db.models import (
    AllocationStrategyRecord,
    AuditLogRecord,
    AuthRefreshTokenRecord,
    UserProfileRecord,
    UserRecord,
)


class AuthError(Exception):
    pass


class EmailAlreadyRegisteredError(AuthError):
    pass


class InvalidCredentialsError(AuthError):
    pass


class InvalidRefreshTokenError(AuthError):
    pass


def register_user(
    db: Session,
    email: str,
    password: str,
    name: str | None,
    base_currency: str,
) -> tuple[UserRecord, str, str]:
    existing_user = db.scalar(select(UserRecord).where(UserRecord.email == email))
    if existing_user is not None:
        raise EmailAlreadyRegisteredError("User with this email already exists")

    user = UserRecord(email=email, password_hash=hash_password(password))
    db.add(user)
    db.flush()

    db.add(
        UserProfileRecord(
            user_id=user.id,
            name=name,
            base_currency=base_currency,
        )
    )
    db.add(AllocationStrategyRecord(user_id=user.id))

    refresh_token = issue_refresh_token(db, user.id)
    access_token = create_access_token(user.id)
    db.commit()
    db.refresh(user)
    return user, access_token, refresh_token


def authenticate_user(
    db: Session,
    email: str,
    password: str,
) -> tuple[UserRecord, str, str]:
    user = db.scalar(select(UserRecord).where(UserRecord.email == email))
    if user is None or user.deleted_at is not None:
        raise InvalidCredentialsError("Invalid email or password")
    if not verify_password(password, user.password_hash):
        raise InvalidCredentialsError("Invalid email or password")

    refresh_token = issue_refresh_token(db, user.id)
    access_token = create_access_token(user.id)
    db.commit()
    return user, access_token, refresh_token


def rotate_refresh_token(db: Session, refresh_token: str) -> tuple[UserRecord, str, str]:
    token_record = get_active_refresh_token(db, refresh_token)
    if token_record is None:
        raise InvalidRefreshTokenError("Invalid refresh token")

    user = db.get(UserRecord, token_record.user_id)
    if user is None or user.deleted_at is not None:
        raise InvalidRefreshTokenError("Invalid refresh token")

    new_refresh_token = issue_refresh_token(db, user.id)
    new_token_record = db.scalar(
        select(AuthRefreshTokenRecord).where(
            AuthRefreshTokenRecord.token_hash == hash_refresh_token(new_refresh_token)
        )
    )
    token_record.revoked_at = datetime.now(UTC)
    token_record.replaced_by_token_id = new_token_record.id if new_token_record else None

    access_token = create_access_token(user.id)
    db.commit()
    return user, access_token, new_refresh_token


def revoke_refresh_token(db: Session, refresh_token: str) -> bool:
    token_record = get_active_refresh_token(db, refresh_token)
    if token_record is None:
        return False
    token_record.revoked_at = datetime.now(UTC)
    db.commit()
    return True


def delete_user_account(db: Session, user_id: str) -> UserRecord:
    user = db.get(UserRecord, user_id)
    if user is None or user.deleted_at is not None:
        raise InvalidCredentialsError("Unknown user")

    now = datetime.now(UTC)
    before = {
        "id": user.id,
        "email": user.email,
        "deleted_at": user.deleted_at.isoformat() if user.deleted_at else None,
    }
    user.email = f"deleted-{user.id}@deleted.local"
    user.password_hash = None
    user.deleted_at = now

    active_tokens = db.scalars(
        select(AuthRefreshTokenRecord).where(
            AuthRefreshTokenRecord.user_id == user_id,
            AuthRefreshTokenRecord.revoked_at.is_(None),
        )
    ).all()
    for token_record in active_tokens:
        token_record.revoked_at = now

    db.add(
        AuditLogRecord(
            actor_user_id=user_id,
            entity_type="user",
            entity_id=user_id,
            action="delete_account",
            before_json=before,
            after_json={
                "id": user.id,
                "email": user.email,
                "deleted_at": now.isoformat(),
                "revoked_refresh_tokens": len(active_tokens),
            },
        )
    )
    db.commit()
    db.refresh(user)
    return user


def issue_refresh_token(db: Session, user_id: str) -> str:
    refresh_token = create_refresh_token_value()
    db.add(
        AuthRefreshTokenRecord(
            user_id=user_id,
            token_hash=hash_refresh_token(refresh_token),
            expires_at=refresh_token_expiry(),
        )
    )
    return refresh_token


def get_active_refresh_token(
    db: Session,
    refresh_token: str,
) -> AuthRefreshTokenRecord | None:
    token_record = db.scalar(
        select(AuthRefreshTokenRecord).where(
            AuthRefreshTokenRecord.token_hash == hash_refresh_token(refresh_token)
        )
    )
    if token_record is None:
        return None
    if token_record.revoked_at is not None:
        return None
    if as_utc(token_record.expires_at) <= datetime.now(UTC):
        return None
    return token_record


def as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
