# ecrf_backend/main.py — drop-in
import os
from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

from .database import Base, engine, SessionLocal
from .logger import logger
from .auth import hash_password
from . import models

from .users import router as users_router
from .forms import router as forms_router
from .api import router as api_router
from .audit import router as audit_router
from .obi_api import router as obi_router
app = FastAPI()

# CORS (not needed for packaged same-origin, but fine for dev)
ALLOWED_ORIGINS = [
    "http://localhost:8080",
    "http://127.0.0.1:8080",
    "http://localhost:8001",
    "http://127.0.0.1:8001",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(users_router)
app.include_router(forms_router)
app.include_router(api_router)
app.include_router(audit_router)
app.include_router(obi_router)
# Tables
Base.metadata.create_all(bind=engine)


def _ensure_default_user(db, username: str, email: str, password: str,
                         first_name: str, last_name: str, role: str):
    """Create user+profile with given role if missing. Does not overwrite existing users."""
    u = db.query(models.User).filter(models.User.username == username).first()
    if u:
        if not u.profile:
            p = models.UserProfile(user_id=u.id, first_name=first_name, last_name=last_name, role=role)
            db.add(p); db.commit(); db.refresh(p)
            logger.info(f"Added profile for existing user '{username}' with role '{role}'.")
        return

    u = models.User(username=username, email=email, password=hash_password(password))
    db.add(u); db.commit(); db.refresh(u)

    p = models.UserProfile(user_id=u.id, first_name=first_name, last_name=last_name, role=role)
    db.add(p); db.commit(); db.refresh(p)
    logger.info(f"Seeded user '{username}' with role '{role}'.")


def _seed_default_users_if_empty() -> None:
    """
    On a brand-new DB (no users), create:
      - admin / Administrator
      - pi / Principal Investigator
      - investigator / Investigator
    Passwords can be overridden via env vars:
      ECRF_DEFAULT_ADMIN_PASSWORD, ECRF_DEFAULT_PI_PASSWORD, ECRF_DEFAULT_INV_PASSWORD
    """
    db = SessionLocal()
    try:
        has_any = db.query(models.User).first() is not None
        if has_any:
            logger.info("Users table not empty — skipping default user seed.")
            return

        admin_pw = os.getenv("ECRF_DEFAULT_ADMIN_PASSWORD", "Admin123!")
        # Keeping only admin as the default User and with Administrator privileges.
        # Users are advised to change password later and create new Users with different privileges
        #pi_pw    = os.getenv("ECRF_DEFAULT_PI_PASSWORD",    "Pi123!")
        #inv_pw   = os.getenv("ECRF_DEFAULT_INV_PASSWORD",   "Investigator123!")

        _ensure_default_user(db, "admin",        "admin@example.com",        admin_pw, "Admin",        "User", "Administrator")
        #_ensure_default_user(db, "pi_user",           "pi@example.com",           pi_pw,    "Principal",    "Investigator", "Principal Investigator")
        #_ensure_default_user(db, "investigator", "investigator@example.com", inv_pw,   "Investigator", "User", "Investigator")

        logger.info("Default users seeded (admin).")
    except Exception as e:
        logger.error(f"Default user seed failed: {e}")
        db.rollback()
    finally:
        db.close()




@app.on_event("startup")
async def startup_event():
    logger.info("Application has started.")
    # Seed defaults if this is a brand-new DB
    _seed_default_users_if_empty()


@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Application has stopped.")


@app.get("/health")
async def health_check():
    return {"status": "ok"}
