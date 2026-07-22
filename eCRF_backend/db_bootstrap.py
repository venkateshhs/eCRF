from __future__ import annotations

from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

from . import models
from .auth import hash_password
from .database import Base, SessionLocal, engine
from .logger import logger
from .settings import get_settings

settings = get_settings()

LEGACY_INVALID_ADMIN_EMAILS = {"admin@case-e.local"}
DEFAULT_LOCAL_ADMIN_EMAIL = "admin@case-e.org"


def normalize_bootstrap_admin_email(email: str | None) -> str:
    candidate = (email or "").strip()
    if not candidate or candidate.lower() in LEGACY_INVALID_ADMIN_EMAILS:
        return DEFAULT_LOCAL_ADMIN_EMAIL
    return candidate


def ensure_tables() -> None:
    if not settings.db_auto_create:
        logger.info("Database auto-create disabled; skipping Base.metadata.create_all()")
        ensure_auth_schema()
        return
    Base.metadata.create_all(bind=engine)
    ensure_auth_schema()
    logger.info("Database tables ensured")


def ensure_auth_schema() -> None:
    inspector = inspect(engine)
    table_names = inspector.get_table_names()
    if "users" not in table_names:
        ensure_entry_progress_schema()
        return

    user_columns = {col["name"] for col in inspector.get_columns("users")}
    if "must_change_password" in user_columns:
        ensure_entry_progress_schema()
        return

    dialect = engine.dialect.name
    default_value = "false" if dialect == "postgresql" else "0"
    with engine.begin() as conn:
        conn.execute(
            text(
                "ALTER TABLE users "
                f"ADD COLUMN must_change_password BOOLEAN NOT NULL DEFAULT {default_value}"
            )
        )
    logger.info("Added users.must_change_password column.")
    ensure_entry_progress_schema()


def ensure_entry_progress_schema() -> None:


    inspector = inspect(engine)
    if "study_entry_data" not in inspector.get_table_names():
        return

    existing = {col["name"] for col in inspector.get_columns("study_entry_data")}
    additions = [
        ("progress_status", "VARCHAR(20)"),
        ("progress_percentage", "INTEGER"),
        ("progress_completed", "INTEGER"),
        ("progress_total", "INTEGER"),
        ("progress_skipped", "INTEGER"),
    ]
    missing = [(name, sql_type) for name, sql_type in additions if name not in existing]
    if not missing:
        return

    with engine.begin() as conn:
        for name, sql_type in missing:
            conn.execute(text(f"ALTER TABLE study_entry_data ADD COLUMN {name} {sql_type}"))

    logger.info(
        "Added study_entry_data progress columns: %s",
        ", ".join(name for name, _ in missing),
    )





def ensure_admin_user() -> None:
    if not settings.bootstrap_admin:
        logger.info("Bootstrap admin disabled; skipping admin user creation")
        return

    if settings.is_production and not settings.admin_password:
        raise RuntimeError(
            "ECRF_BOOTSTRAP_ADMIN=1 in production requires ECRF_ADMIN_PASSWORD to be set."
        )

    username = settings.admin_username
    email = normalize_bootstrap_admin_email(settings.admin_email)
    password = settings.admin_password or "Admin123!"
    first_name = settings.admin_first_name
    last_name = settings.admin_last_name
    role = settings.admin_role

    if settings.is_production and password == "Admin123!":
        raise RuntimeError("Default bootstrap admin password is not allowed in production.")

    db: Session = SessionLocal()
    try:
        existing = db.query(models.User).filter(models.User.username == username).first()

        if existing:
            logger.info("Bootstrap admin already exists: %s", username)
            profile = (
                db.query(models.UserProfile)
                .filter(models.UserProfile.user_id == existing.id)
                .first()
            )
            changed = False

            if (existing.email or "").strip().lower() in LEGACY_INVALID_ADMIN_EMAILS:
                existing.email = email
                changed = True
                logger.info("Repaired legacy bootstrap admin email for: %s", username)

            if profile is None:
                profile = models.UserProfile(
                    user_id=existing.id,
                    first_name=first_name or "Admin",
                    last_name=last_name or "User",
                    role=role or "Administrator",
                )
                db.add(profile)
                changed = True
            else:
                if not profile.first_name and first_name:
                    profile.first_name = first_name
                    changed = True
                if not profile.last_name and last_name:
                    profile.last_name = last_name
                    changed = True
                if not profile.role and role:
                    profile.role = role
                    changed = True

            if changed:
                db.commit()
                logger.info("Bootstrap admin profile synced for: %s", username)
            return

        user = models.User(
            username=username,
            email=email,
            password=hash_password(password),
        )
        db.add(user)
        db.flush()

        profile = models.UserProfile(
            user_id=user.id,
            first_name=first_name or "Admin",
            last_name=last_name or "User",
            role=role or "Administrator",
        )
        db.add(profile)
        db.commit()

        logger.info("Bootstrap admin created: %s", username)
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def init_database_and_admin() -> None:
    ensure_tables()
    ensure_admin_user()
