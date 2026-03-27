# eCRF_backend/database.py
from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

try:
    from sqlalchemy.orm import declarative_base
except Exception:  # pragma: no cover
    from sqlalchemy.ext.declarative import declarative_base  # type: ignore

from .settings import get_settings

settings = get_settings()
DATABASE_URL = settings.database_url

connect_args = {}
engine_kwargs = {}

if DATABASE_URL.startswith("sqlite:"):
    connect_args = {"check_same_thread": False}

engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    pool_pre_ping=True,
    **engine_kwargs,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()