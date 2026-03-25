# eCRF_backend/db_bootstrap.py
from __future__ import annotations

import os

from sqlalchemy.orm import Session

from .database import Base, engine, SessionLocal
from . import models
from .logger import logger
from .auth import hash_password


def _hash_password(password: str) -> str:
    return hash_password(password)


def ensure_tables() -> None:
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables ensured")


def ensure_admin_user() -> None:
    username = os.environ.get("ECRF_ADMIN_USERNAME", "admin").strip()
    email = os.environ.get("ECRF_ADMIN_EMAIL", "admin@case-e.com").strip()
    password = os.environ.get("ECRF_ADMIN_PASSWORD", "Admin123!").strip()

    first_name = os.environ.get("ECRF_ADMIN_FIRST_NAME", "Admin").strip()
    last_name = os.environ.get("ECRF_ADMIN_LAST_NAME", "User").strip()
    role = os.environ.get("ECRF_ADMIN_ROLE", "Administrator").strip()

    db: Session = SessionLocal()
    try:
        existing = db.query(models.User).filter(models.User.username == username).first()
        if existing:
            logger.info("Bootstrap admin already exists: %s", username)

            profile = db.query(models.UserProfile).filter(models.UserProfile.user_id == existing.id).first()
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
                if not profile.first_name:
                    profile.first_name = first_name or "Admin"
                    changed = True
                if not profile.last_name:
                    profile.last_name = last_name or "User"
                    changed = True
                if not profile.role:
                    profile.role = role or "Administrator"
                    changed = True

            if changed:
                db.commit()
                logger.info("Bootstrap admin profile repaired: %s", username)
            return

        user = models.User(
            username=username,
            email=email,
            password=_hash_password(password),
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        profile = models.UserProfile(
            user_id=user.id,
            first_name=first_name or "Admin",
            last_name=last_name or "User",
            role=role or "Administrator",
        )
        db.add(profile)
        db.commit()

        logger.info("Bootstrap admin created: username=%s email=%s", username, email)

    except Exception:
        db.rollback()
        logger.exception("Failed to bootstrap admin user")
        raise
    finally:
        db.close()


def init_database_and_admin() -> None:
    ensure_tables()
    ensure_admin_user()