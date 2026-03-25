from __future__ import annotations

from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

from .database import Base, engine
from .users import router as users_router
from .forms_hybrid import router as forms_router
from .api import router as api_router
from .obi_api import router as obi_router

from .audit_datalad import router as audit_router
from .datalad_api_routes import router as datalad_ops_router
from .datalad_config import get_datalad_config
from .datalad_runtime import init_datalad_runtime, shutdown_datalad_runtime
from .db_bootstrap import init_database_and_admin
from .logger import logger

app = FastAPI(title="case-e (Hybrid DataLad app)")

ALLOWED_ORIGINS = [
    "http://localhost:8080",
    "http://127.0.0.1:8080",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
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

app.include_router(users_router)
app.include_router(forms_router)
app.include_router(api_router)
app.include_router(audit_router)
app.include_router(obi_router)
app.include_router(datalad_ops_router)

Base.metadata.create_all(bind=engine)


@app.on_event("startup")
async def _startup():
    init_database_and_admin()
    init_datalad_runtime()
    cfg = get_datalad_config()
    logger.info(
        "Hybrid app startup complete mode=%s sync_mode=%s",
        cfg.mode,
        getattr(cfg, "sync_mode", None),
    )


@app.on_event("shutdown")
async def _shutdown():
    shutdown_datalad_runtime()


@app.get("/health")
async def health_check():
    cfg = get_datalad_config()
    return {
        "status": "ok",
        "datalad_mode": cfg.mode,
        "sync_mode": getattr(cfg, "sync_mode", None),
    }