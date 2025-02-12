from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Header   
from sqlalchemy.orm import Session
from schemas import UserCreate, LoginRequest, UserResponse
from crud import get_user_by_username, create_user
from auth import hash_password, verify_password, create_access_token
from database import get_db
from logger import logger
from models import User, UserProfile
import jwt
import re
from fastapi.security import OAuth2PasswordBearer
from jwt import decode, ExpiredSignatureError, InvalidTokenError
SECRET_KEY = "your-very-secure-secret-key"
ALGORITHM = "HS256"

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="users/login")

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

    # Fetch user from the database
    user = get_user_by_username(db, request.username)
    if not user:
        logger.warning(f"Login failed: Username not found: {request.username}")
        raise HTTPException(status_code=400, detail="Invalid username or password.")

    logger.debug(f"Stored password for {request.username}: {user.password}")
    logger.debug(f"Password entered: {request.password}")

    if not verify_password(request.password, user.password):
        logger.warning(f"Login failed: Incorrect password for {request.username}")
        raise HTTPException(status_code=400, detail="Invalid username or password.")

    # Generate token
    token = create_access_token(user.username)
    logger.info(f"User {request.username} logged in successfully.")
    return {"access_token": token, "token_type": "bearer"}

@router.post("/change-password")
def change_password(username: str, new_password: str, db: Session = Depends(get_db)):
    logger.info(f"Password change request for user: {username}")

    user = get_user_by_username(db, username)
    if not user:
        logger.warning(f"Password change failed: User not found: {username}")
        raise HTTPException(status_code=404, detail="User not found.")

    # Validate new password
    password_regex = re.compile(r"^(?=.*[0-9])(?=.*[!@#$%^&*])[A-Za-z\d!@#$%^&*]{8,}$")
    if not password_regex.match(new_password):
        logger.warning(f"Password validation failed for user: {username}")
        raise HTTPException(
            status_code=400,
            detail="Password must be at least 8 characters, include a number, and a special character.",
        )

    # Hash and update the new password
    user.password = hash_password(new_password)
    db.commit()

    logger.info(f"Password successfully changed for user: {username}")
    return {"message": "Password changed successfully"}


@router.get("/me", response_model=UserResponse)
def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    username = payload.get("sub")
    if username is None:
        raise HTTPException(status_code=401, detail="Invalid token")

    user = get_user_by_username(db, username)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return user


def get_current_user(authorization: str = Header(None), db: Session = Depends(get_db)) -> User:
    """
    Decodes the JWT access token from the Authorization header and retrieves the authenticated user object.
    """
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header missing")

    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authorization header must start with 'Bearer '")

    token = authorization.split("Bearer ")[1]
    try:
        payload = decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        exp = payload.get("exp")

        if not username or not exp:
            raise HTTPException(status_code=401, detail="Invalid token payload")

        if datetime.utcnow().timestamp() > exp:
            raise HTTPException(status_code=401, detail="Token expired")

        user = db.query(User).filter(User.username == username).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        logger.info(f"User {user.username} authenticated successfully.")
        return user

    except ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")



