# ecrf_backend/database.py
import os
import sys
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# SQLAlchemy import is different across versions; keep this fallback for safety
try:
    from sqlalchemy.orm import declarative_base  # SQLAlchemy ≥1.4
except Exception:  # pragma: no cover
    from sqlalchemy.ext.declarative import declarative_base  # SQLAlchemy <1.4


def _runtime_data_dir() -> Path:
    """
    Choose a writable, persistent directory for the SQLite DB and other artifacts.
    Priority:
      1) ECRF_DATA_DIR (set by server.py at runtime)
      2) Next to the executable (PyInstaller frozen)
      3) Repo/dev fallback: ecrf_backend/data next to this file
    """
    env = os.environ.get("ECRF_DATA_DIR")
    if env:
        return Path(env)

    if getattr(sys, "frozen", False):
        # Running from a PyInstaller bundle: use a folder next to the EXE
        return Path(sys.executable).resolve().parent / "ecrf_data"

    # Dev mode: keep using a local 'data' folder under the package
    return Path(__file__).resolve().parent / "data"


DATA_DIR = _runtime_data_dir()
DATA_DIR.mkdir(parents=True, exist_ok=True)

DB_PATH = DATA_DIR / "ecrf.db"
DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},  # needed for SQLite with FastAPI
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
