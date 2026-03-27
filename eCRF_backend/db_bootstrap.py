from __future__ import annotations

from sqlalchemy.orm import Session

from . import models
from .auth import hash_password
from .database import Base, SessionLocal, engine
from .logger import logger
from .settings import get_settings

settings = get_settings()


def ensure_tables() -> None:
    if not settings.db_auto_create:
        logger.info("Database auto-create disabled; skipping Base.metadata.create_all()")
        return
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables ensured")


def ensure_admin_user() -> None:
    if not settings.bootstrap_admin:
        logger.info("Bootstrap admin disabled; skipping admin user creation")
        return

    if settings.is_production and not settings.admin_password:
        raise RuntimeError(
            "ECRF_BOOTSTRAP_ADMIN=1 in production requires ECRF_ADMIN_PASSWORD to be set."
        )

    username = settings.admin_username
    email = settings.admin_email
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