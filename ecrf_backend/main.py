from fastapi import FastAPI

from database import Base, engine
import users

from logger import logger

# Create database tables
try:
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created successfully.")
except Exception as e:
    logger.error(f"Error creating database tables: {e}")

# FastAPI app setup
app = FastAPI()

# Include user-related routes
app.include_router(users.router)

@app.on_event("startup")
def on_startup():
    logger.info("Application has started.")

@app.on_event("shutdown")
def on_shutdown():
    logger.info("Application has stopped.")
