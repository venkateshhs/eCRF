from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware
import users
from database import Base, engine
from logger import logger

# Initialize FastAPI app
app = FastAPI()
ALLOWED_ORIGINS = '*'
# Allow CORS for localhost during development
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,  # Frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(users.router)

# Database initialization
Base.metadata.create_all(bind=engine)

@app.on_event("startup")
async def startup_event():
    logger.info("Application has started.")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Application has stopped.")
