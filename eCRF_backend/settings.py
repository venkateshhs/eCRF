# eCRF_backend/settings.py
from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Optional, Tuple


def _as_bool(value: Optional[str], default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _as_csv(value: Optional[str]) -> Tuple[str, ...]:
    if not value:
        return tuple()
    return tuple(x.strip() for x in value.split(",") if x.strip())


def _runtime_data_dir_fallback() -> Path:
    env = os.environ.get("ECRF_DATA_DIR")
    if env:
        return Path(env).expanduser().resolve()

    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent / "ecrf_data"

    return Path(__file__).resolve().parent / "data"


def _detect_profile(env: str) -> str:
    """Select local versus hosted behavior without requiring a manual switch."""
    explicit = (os.getenv("ECRF_PROFILE") or "").strip().lower()
    if explicit:
        if explicit in {"hosted", "production"}:
            return "server"
        return explicit

    if getattr(sys, "frozen", False):
        return "local"

    database_url = (os.getenv("ECRF_DATABASE_URL") or os.getenv("DATABASE_URL") or "").lower()
    if (
        env == "production"
        or os.getenv("ECRF_DATALAD_RIA_URL")
        or database_url.startswith(("postgresql:", "postgres:"))
    ):
        return "server"

    return "local"


@dataclass(frozen=True)
class AppSettings:
    env: str
    profile: str

    database_url: str
    db_auto_create: bool
    allow_sqlite_in_production: bool

    secret_key: str
    jwt_algorithm: str
    password_hashing_enabled: bool

    password_reset_enabled: bool
    password_reset_ttl_minutes: int
    password_reset_confirmation_ttl_minutes: int
    password_reset_max_per_user_hour: int
    password_reset_max_lookups_per_ip_hour: int
    frontend_base_url: str

    smtp_host: str
    smtp_port: int
    smtp_username: Optional[str]
    smtp_password: Optional[str]
    smtp_starttls: bool
    smtp_ssl: bool
    smtp_timeout_seconds: float
    mail_from: str

    cors_allow_origins: Tuple[str, ...]
    cors_allow_origin_regex: Optional[str]

    bind_host: str
    port: int
    open_browser: bool
    trust_proxy_headers: bool

    data_dir: Path
    bids_root: Path
    templates_dir: Optional[Path]

    bootstrap_admin: bool
    admin_username: str
    admin_email: str
    admin_password: Optional[str]
    admin_first_name: str
    admin_last_name: str
    admin_role: str

    datalad_required_in_production: bool
    datalad_lock_timeout_seconds: float

    @property
    def is_production(self) -> bool:
        return self.env == "production"

    @property
    def is_local_profile(self) -> bool:
        return self.profile == "local"

    def validate(self) -> None:
        errors = []

        if self.is_production:
            if not self.database_url:
                errors.append("ECRF_DATABASE_URL must be set in production.")
            if self.database_url.startswith("sqlite:") and not self.allow_sqlite_in_production:
                errors.append("SQLite is not allowed in production unless ECRF_ALLOW_SQLITE_IN_PRODUCTION=1.")

            if not self.secret_key or self.secret_key == "your-very-secure-secret-key":
                errors.append("ECRF_SECRET_KEY must be set to a strong non-default value in production.")

            if not self.cors_allow_origins and not self.cors_allow_origin_regex:
                errors.append(
                    "Set ECRF_CORS_ALLOW_ORIGINS or ECRF_CORS_ALLOW_ORIGIN_REGEX in production."
                )

            if self.datalad_required_in_production:
                if not self.data_dir:
                    errors.append("ECRF_DATA_DIR must be set in production.")
                if not self.bids_root:
                    errors.append("BIDS_ROOT must be set in production.")

            if self.bootstrap_admin and not self.admin_password:
                errors.append(
                    "ECRF_ADMIN_PASSWORD must be set when ECRF_BOOTSTRAP_ADMIN=1 in production."
                )

        if self.password_reset_enabled:
            if not self.frontend_base_url:
                errors.append("ECRF_FRONTEND_BASE_URL must be set when password reset is enabled.")
            if not self.smtp_host:
                errors.append("ECRF_SMTP_HOST must be set when password reset is enabled.")
            if not self.mail_from:
                errors.append("ECRF_MAIL_FROM must be set when password reset is enabled.")
            if self.smtp_starttls and self.smtp_ssl:
                errors.append("Only one of ECRF_SMTP_STARTTLS and ECRF_SMTP_SSL may be enabled.")
            if bool(self.smtp_username) != bool(self.smtp_password):
                errors.append(
                    "ECRF_SMTP_USERNAME and ECRF_SMTP_PASSWORD must either both be set or both be empty."
                )
            if self.password_reset_ttl_minutes < 1:
                errors.append("ECRF_PASSWORD_RESET_TTL_MINUTES must be at least 1.")
            if self.password_reset_confirmation_ttl_minutes < 1:
                errors.append("ECRF_PASSWORD_RESET_CONFIRMATION_TTL_MINUTES must be at least 1.")

        if errors:
            raise RuntimeError("Invalid case-e configuration:\n- " + "\n- ".join(errors))


@lru_cache(maxsize=1)
def get_settings() -> AppSettings:
    env = (os.getenv("ECRF_ENV", "development") or "development").strip().lower()
    profile = _detect_profile(env)

    data_dir = _runtime_data_dir_fallback()
    bids_root = Path(os.getenv("BIDS_ROOT", str(data_dir / "bids_datasets"))).expanduser().resolve()

    templates_dir_raw = os.getenv("ECRF_TEMPLATES_DIR")
    templates_dir = Path(templates_dir_raw).expanduser().resolve() if templates_dir_raw else None

    database_url = (
        os.getenv("ECRF_DATABASE_URL")
        or os.getenv("DATABASE_URL")
        or f"sqlite:///{(data_dir / 'ecrf.db').resolve()}"
    )

    settings = AppSettings(
        env=env,
        profile=profile,
        database_url=database_url,
        db_auto_create=_as_bool(os.getenv("ECRF_DB_AUTO_CREATE"), default=(env != "production")),
        allow_sqlite_in_production=_as_bool(os.getenv("ECRF_ALLOW_SQLITE_IN_PRODUCTION"), default=False),
        secret_key=os.getenv("ECRF_SECRET_KEY", "your-very-secure-secret-key"),
        jwt_algorithm=os.getenv("ECRF_JWT_ALGORITHM", "HS256"),
        password_hashing_enabled=_as_bool(os.getenv("ECRF_PASSWORD_HASHING_ENABLED"), default=True),
        password_reset_enabled=_as_bool(os.getenv("ECRF_PASSWORD_RESET_ENABLED"), default=False),
        password_reset_ttl_minutes=int(os.getenv("ECRF_PASSWORD_RESET_TTL_MINUTES", "20")),
        password_reset_confirmation_ttl_minutes=int(
            os.getenv("ECRF_PASSWORD_RESET_CONFIRMATION_TTL_MINUTES", "10")
        ),
        password_reset_max_per_user_hour=int(
            os.getenv("ECRF_PASSWORD_RESET_MAX_PER_USER_HOUR", "3")
        ),
        password_reset_max_lookups_per_ip_hour=int(
            os.getenv("ECRF_PASSWORD_RESET_MAX_LOOKUPS_PER_IP_HOUR", "10")
        ),
        frontend_base_url=os.getenv("ECRF_FRONTEND_BASE_URL", "").strip().rstrip("/"),
        smtp_host=os.getenv("ECRF_SMTP_HOST", "").strip(),
        smtp_port=int(os.getenv("ECRF_SMTP_PORT", "587")),
        smtp_username=(os.getenv("ECRF_SMTP_USERNAME") or "").strip() or None,
        smtp_password=(os.getenv("ECRF_SMTP_PASSWORD") or "").strip() or None,
        smtp_starttls=_as_bool(os.getenv("ECRF_SMTP_STARTTLS"), default=True),
        smtp_ssl=_as_bool(os.getenv("ECRF_SMTP_SSL"), default=False),
        smtp_timeout_seconds=float(os.getenv("ECRF_SMTP_TIMEOUT_SECONDS", "15")),
        mail_from=os.getenv("ECRF_MAIL_FROM", "").strip(),
        cors_allow_origins=_as_csv(os.getenv("ECRF_CORS_ALLOW_ORIGINS")),
        cors_allow_origin_regex=os.getenv("ECRF_CORS_ALLOW_ORIGIN_REGEX") or None,
        bind_host=os.getenv("ECRF_BIND_HOST", "127.0.0.1" if profile == "local" else "0.0.0.0"),
        port=int(os.getenv("ECRF_PORT", "8000")),
        open_browser=_as_bool(os.getenv("ECRF_OPEN_BROWSER"), default=(profile == "local")),
        trust_proxy_headers=_as_bool(
            os.getenv("ECRF_TRUST_PROXY_HEADERS"), default=(profile == "server")
        ),
        data_dir=data_dir,
        bids_root=bids_root,
        templates_dir=templates_dir,
        bootstrap_admin=_as_bool(os.getenv("ECRF_BOOTSTRAP_ADMIN"), default=(env != "production")),
        admin_username=os.getenv("ECRF_ADMIN_USERNAME", "admin").strip(),
        admin_email=os.getenv("ECRF_ADMIN_EMAIL", "admin@case-e.com").strip(),
        admin_password=(os.getenv("ECRF_ADMIN_PASSWORD") or "").strip() or None,
        admin_first_name=os.getenv("ECRF_ADMIN_FIRST_NAME", "Admin").strip(),
        admin_last_name=os.getenv("ECRF_ADMIN_LAST_NAME", "User").strip(),
        admin_role=os.getenv("ECRF_ADMIN_ROLE", "Administrator").strip(),
        datalad_required_in_production=_as_bool(
            os.getenv("ECRF_DATALAD_REQUIRED_IN_PRODUCTION"), default=True
        ),
        datalad_lock_timeout_seconds=float(os.getenv("ECRF_DATALAD_LOCK_TIMEOUT_SECONDS", "60")),
    )

    settings.data_dir.mkdir(parents=True, exist_ok=True)
    settings.bids_root.mkdir(parents=True, exist_ok=True)
    settings.validate()
    return settings
