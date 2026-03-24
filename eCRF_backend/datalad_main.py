from __future__ import annotations

from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

from .users import router as users_router
from .forms_datalad import router as forms_router
from .datalad_api_routes import router as datalad_ops_router
from .datalad_config import get_datalad_config
from .logger import logger

app = FastAPI(title="case-e (DataLad backend)")

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

# keep users router for auth only
app.include_router(users_router)

# DataLad-native forms router
app.include_router(forms_router)

# optional datalad ops router
app.include_router(datalad_ops_router)


@app.on_event("startup")
async def _startup():
    logger.info("DataLad app startup complete mode=%s", get_datalad_config().mode)


@app.get("/health")
async def health_check():
    return {
        "status": "ok",
        "datalad_mode": get_datalad_config().mode,
        "backend": "datalad",
    }