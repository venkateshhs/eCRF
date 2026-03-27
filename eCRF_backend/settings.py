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

    cors_allow_origins: Tuple[str, ...]
    cors_allow_origin_regex: Optional[str]

    bind_host: str
    port: int
    open_browser: bool

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

        if errors:
            raise RuntimeError("Invalid case-e configuration:\n- " + "\n- ".join(errors))


@lru_cache(maxsize=1)
def get_settings() -> AppSettings:
    env = (os.getenv("ECRF_ENV", "development") or "development").strip().lower()
    profile = (os.getenv("ECRF_PROFILE", "local" if env != "production" else "server") or "server").strip().lower()

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
        cors_allow_origins=_as_csv(os.getenv("ECRF_CORS_ALLOW_ORIGINS")),
        cors_allow_origin_regex=os.getenv("ECRF_CORS_ALLOW_ORIGIN_REGEX") or None,
        bind_host=os.getenv("ECRF_BIND_HOST", "127.0.0.1" if profile == "local" else "0.0.0.0"),
        port=int(os.getenv("ECRF_PORT", "8000")),
        open_browser=_as_bool(os.getenv("ECRF_OPEN_BROWSER"), default=(profile == "local")),
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