from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from schemas import UserCreate, LoginRequest, UserResponse
from crud import get_user_by_username, get_user_by_email, create_user
from auth import hash_password, verify_password, create_access_token
from database import get_db
from logger import logger
from models import User, UserProfile  # Import the User model

logger.info("Its here.")
router = APIRouter(prefix="/users", tags=["users"])


@router.post("/register", response_model=UserResponse)
def register_user(user_data: UserCreate, db: Session = Depends(get_db)):
    logger.info("Attempting to register a new user.")

    # Check if user already exists
    existing_user = db.query(User).filter(
        (User.username == user_data.username) | (User.email == user_data.email)
    ).first()
    if existing_user:
        logger.warning(f"User registration failed. Username or email already exists: {user_data.username}")
        raise HTTPException(status_code=400, detail="Username or email already exists.")

    # Hash the password
    hashed_password = hash_password(user_data.password)

    # Create the user object
    user = User(
        username=user_data.username,
        email=user_data.email,
        password=hashed_password
    )
    db.add(user)  # Add the user to the session
    db.commit()  # Commit the transaction
    db.refresh(user)  # Refresh the instance to update fields like `id`

    # Create a profile for the user
    profile = UserProfile(
        user_id=user.id,
        first_name=user_data.first_name,
        last_name=user_data.last_name
    )
    db.add(profile)  # Add the profile to the session
    db.commit()  # Commit the transaction
    db.refresh(profile)  # Refresh the instance

    logger.info(f"User {user.username} registered successfully.")
    return user

@router.post("/login")
def login_user(request: LoginRequest, db: Session = Depends(get_db)):
    logger.info(f"Login attempt for username: {request.username}")
    user = get_user_by_username(db, request.username)
    if not user or not verify_password(request.password, user.password):
        logger.warning(f"Failed login for username: {request.username}")
        raise HTTPException(status_code=400, detail="Invalid username or password.")

    token = create_access_token(user.username)
    logger.info(f"User {request.username} logged in successfully.")
    return {"access_token": token, "token_type": "bearer"}
