# eCRF_backend/datalad_main.py
from __future__ import annotations

import asyncio
import contextlib
import os

from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

from .api import router as api_router
from .audit_datalad import router as audit_router
from .datalad_api_routes import router as datalad_ops_router
from .datalad_config import get_datalad_config
from .datalad_runtime import init_datalad_runtime, shutdown_datalad_runtime
from .db_bootstrap import init_database_and_admin
from .database import SessionLocal
from .forms_hybrid import router as forms_router
from .logger import logger
from .obi_api import router as obi_router
from .pending_remote_deletes import retry_pending_remote_deletes
from .settings import get_settings
from .study_activity import sync_and_remove_unaccessed_studies
from .users import router as users_router
from .saved_form_templates import router as saved_form_templates
settings = get_settings()
cfg = get_datalad_config()

app = FastAPI(title="case-e (Hybrid DataLad app)")
_study_activity_sync_task: asyncio.Task | None = None
_study_activity_sync_lock: asyncio.Lock | None = None


def _study_activity_sync_interval_seconds() -> int:
    try:
        return max(0, int(os.getenv("ECRF_STUDY_ACTIVITY_SYNC_INTERVAL_SECONDS", "300")))
    except Exception:
        return 300


def _run_study_activity_cleanup(reason: str) -> None:
    db = SessionLocal()
    try:
        sync_and_remove_unaccessed_studies(db, reason=reason)
    finally:
        db.close()


async def _run_study_activity_cleanup_once(reason: str) -> None:
    global _study_activity_sync_lock
    if _study_activity_sync_lock is None:
        _study_activity_sync_lock = asyncio.Lock()
    if _study_activity_sync_lock.locked():
        logger.info("Study activity sync cleanup already running; skipping reason=%s", reason)
        return
    async with _study_activity_sync_lock:
        await asyncio.to_thread(_run_study_activity_cleanup, reason)


async def _study_activity_sync_loop() -> None:
    interval_seconds = _study_activity_sync_interval_seconds()
    if interval_seconds <= 0:
        logger.info("Study activity background sync cleanup disabled")
        return

    reason = "startup"
    while True:
        try:
            await _run_study_activity_cleanup_once(reason)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Study activity background sync cleanup failed")
        reason = "background_sync"
        await asyncio.sleep(interval_seconds)

cors_kwargs = {
    "allow_credentials": True,
    "allow_methods": ["*"],
    "allow_headers": ["*"],
}
if settings.cors_allow_origin_regex:
    cors_kwargs["allow_origin_regex"] = settings.cors_allow_origin_regex
else:
    cors_kwargs["allow_origins"] = list(settings.cors_allow_origins)

app.add_middleware(CORSMiddleware, **cors_kwargs)

app.include_router(users_router)
app.include_router(forms_router)
app.include_router(api_router)
app.include_router(audit_router)
app.include_router(obi_router)
app.include_router(datalad_ops_router)
app.include_router(saved_form_templates)

@app.on_event("startup")
async def _startup():
    global _study_activity_sync_task
    init_database_and_admin()
    init_datalad_runtime()
    db = SessionLocal()
    try:
        retry_pending_remote_deletes(db)
    finally:
        db.close()
    interval_seconds = _study_activity_sync_interval_seconds()
    if interval_seconds > 0:
        _study_activity_sync_task = asyncio.create_task(_study_activity_sync_loop())
        logger.info("Study activity background sync cleanup scheduled interval_seconds=%s", interval_seconds)
    logger.info(
        "Hybrid app startup complete env=%s mode=%s sync_mode=%s db_auto_create=%s",
        settings.env,
        cfg.mode,
        cfg.sync_mode,
        settings.db_auto_create,
    )


@app.on_event("shutdown")
async def _shutdown():
    global _study_activity_sync_task
    if _study_activity_sync_task is not None:
        _study_activity_sync_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await _study_activity_sync_task
        _study_activity_sync_task = None
    shutdown_datalad_runtime()
    logger.info("Hybrid app shutdown complete")


@app.get("/health")
async def health():
    return {
        "ok": True,
        "env": settings.env,
        "db": "sqlite" if settings.database_url.startswith("sqlite:") else "server",
        "datalad_mode": cfg.mode,
        "datalad_sync_mode": cfg.sync_mode,
        "ria_configured": bool(cfg.ria_url),
        "push_on_save": cfg.push_on_save,
    }
