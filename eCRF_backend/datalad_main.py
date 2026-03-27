# eCRF_backend/datalad_main.py
from __future__ import annotations

from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

from .api import router as api_router
from .audit_datalad import router as audit_router
from .datalad_api_routes import router as datalad_ops_router
from .datalad_config import get_datalad_config
from .datalad_runtime import init_datalad_runtime, shutdown_datalad_runtime
from .db_bootstrap import init_database_and_admin
from .forms_hybrid import router as forms_router
from .logger import logger
from .obi_api import router as obi_router
from .settings import get_settings
from .users import router as users_router

settings = get_settings()
cfg = get_datalad_config()

app = FastAPI(title="case-e (Hybrid DataLad app)")

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


@app.on_event("startup")
async def _startup():
    init_database_and_admin()
    init_datalad_runtime()
    logger.info(
        "Hybrid app startup complete env=%s mode=%s sync_mode=%s db_auto_create=%s",
        settings.env,
        cfg.mode,
        cfg.sync_mode,
        settings.db_auto_create,
    )


@app.on_event("shutdown")
async def _shutdown():
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