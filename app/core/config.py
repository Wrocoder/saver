from dataclasses import dataclass
from os import getenv


def env_bool(name: str, default: bool) -> bool:
    value = getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True, slots=True)
class Settings:
    database_url: str = getenv("DATABASE_URL", "sqlite:///./money_saver.db")
    demo_user_email: str = getenv("DEMO_USER_EMAIL", "demo@money-saver.local")
    secret_key: str = getenv(
        "SECRET_KEY",
        "dev-only-change-me-money-saver-local-secret-key",
    )
    access_token_expire_minutes: int = int(getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
    refresh_token_expire_days: int = int(getenv("REFRESH_TOKEN_EXPIRE_DAYS", "30"))
    dev_auth_fallback_enabled: bool = env_bool("DEV_AUTH_FALLBACK_ENABLED", True)
    cors_origins: tuple[str, ...] = tuple(
        origin.strip()
        for origin in getenv(
            "CORS_ORIGINS",
            "http://127.0.0.1:5173,http://localhost:5173",
        ).split(",")
        if origin.strip()
    )
    jwt_algorithm: str = "HS256"


settings = Settings()
