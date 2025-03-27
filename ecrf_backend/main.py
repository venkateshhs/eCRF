from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware
import users
from database import Base, engine
import forms
from logger import logger
import api

# Initialize FastAPI app
app = FastAPI()

# Allow CORS for frontend during development
ALLOWED_ORIGINS = ["http://localhost:8080", "http://127.0.0.1:8080", "http://192.168.0.207:8080"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(users.router)
app.include_router(forms.router)
app.include_router(api.router)
# Database initialization
Base.metadata.create_all(bind=engine)

@app.on_event("startup")
async def startup_event():
    logger.info("Application has started.")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Application has stopped.")
    # Add cleanup logic if needed

@app.get("/health")
async def health_check():
    return {"status": "ok"}
