# eCRF_backend/users.py
from datetime import datetime
import jwt
import re
from fastapi import APIRouter, Depends, HTTPException, Header, status
from fastapi.security import OAuth2PasswordBearer
from jwt import decode, ExpiredSignatureError, InvalidTokenError
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel, Field

from . import schemas, models
from .schemas import LoginRequest, UserResponse, UserRegister
from .crud import get_user_by_username  # create_user not used here
from .auth import hash_password, verify_password, create_access_token
from .database import get_db
from .logger import logger

# unified audit (DB + optional BIDS)
from .bids_exporter import audit_change_both

# --------------------------------------------------------------------
# Security config
# --------------------------------------------------------------------
SECRET_KEY = "your-very-secure-secret-key"
ALGORITHM = "HS256"

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="users/login")

router = APIRouter(prefix="/users", tags=["users"])


def _display_name(u: Optional[models.User]) -> str:
    if not u:
        return ""
    prof = getattr(u, "profile", None)
    first = getattr(prof, "first_name", "") or ""
    last = getattr(prof, "last_name", "") or ""
    full = (first + " " + last).strip()
    return full or u.username or u.email or f"User#{u.id}"


def get_current_user(
    authorization: str = Header(None),
    db: Session = Depends(get_db)
) -> models.User:
    """
    Header-based JWT decoding helper for protected endpoints (no audit).
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

        user = db.query(models.User).filter(models.User.username == username).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        logger.info("User %s authenticated successfully.", user.username)
        return user

    except ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


@router.get("/me", response_model=UserResponse)
def get_current_user_oauth(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    """
    OAuth2PasswordBearer-based /me endpoint (no audit).
    """
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    username = payload.get("sub")
    if username is None:
        raise HTTPException(status_code=401, detail="Invalid token")

    user = get_user_by_username(db, username)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@router.post("/register", response_model=UserResponse)
def register_user(user_data: UserRegister, db: Session = Depends(get_db)):
    logger.info("Attempting to register a new user.")

    # Check if user already exists
    existing_user = db.query(models.User).filter(
        (models.User.username == user_data.username) | (models.User.email == user_data.email)
    ).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Username or email already exists.")

    # Hash the password
    hashed_password = hash_password(user_data.password)

    # Create the user
    user = models.User(
        username=user_data.username,
        email=user_data.email,
        password=hashed_password,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # Create a profile
    profile = models.UserProfile(
        user_id=user.id,
        first_name=user_data.first_name,
        last_name=user_data.last_name,
        role="Investigator",
    )
    db.add(profile)
    db.commit()
    db.refresh(profile)

    logger.info("User %s registered successfully.", user.username)

    # AUDIT: new user created (UI)
    try:
        audit_change_both(
            scope="system",
            action="user_created",
            actor=_display_name(user),
            extra={"username": user.username, "role": profile.role},
            db=db,
            actor_id=user.id,
        )
    except Exception:
        pass

    return user


@router.post("/login")
def login_user(request: LoginRequest, db: Session = Depends(get_db)):
    """
    Note: No audit here (by request). Only return token on success.
    """
    logger.info("Login attempt for username: %s", request.username)

    user = get_user_by_username(db, request.username)
    if not user or not verify_password(request.password, getattr(user, "password", "")):
        raise HTTPException(status_code=400, detail="Invalid username or password.")

    if user.profile and user.profile.role == "No Access":
        raise HTTPException(
            status_code=403,
            detail="Your account does not have permission to access this application.",
        )

    token = create_access_token(user.username)
    logger.info("User %s logged in successfully.", request.username)
    return {"access_token": token, "token_type": "bearer"}


# Request body model (accepts either just new_password, or username + new_password)
class ChangePasswordRequest(BaseModel):
    new_password: str = Field(..., alias="new_password")
    username: Optional[str] = None


PASSWORD_RE = re.compile(r"^(?=.*[0-9])(?=.*[!@#$%^&*])[A-Za-z\d!@#$%^&*]{8,}$")


@router.post("/change-password")
def change_password(
    payload: ChangePasswordRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Change password for the current user (default).
    Admins may optionally include 'username' in the body to change another user's password.
    Body JSON: { "new_password": "...", "username": "optional" }
    """
    target_username = payload.username or getattr(current_user, "username", None)
    if not target_username:
        raise HTTPException(status_code=400, detail="Username resolution failed.")

    if not PASSWORD_RE.match(payload.new_password):
        raise HTTPException(
            status_code=400,
            detail="Password must be at least 8 characters, include a number, and a special character.",
        )

    # Only allow changing own password, unless current user is Administrator
    is_admin = (getattr(current_user, "profile", None) and
                getattr(current_user.profile, "role", "") == "Administrator")
    if payload.username and not is_admin and payload.username != current_user.username:
        raise HTTPException(status_code=403, detail="Not authorized to change another user's password.")

    user = get_user_by_username(db, target_username)
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    user.password = hash_password(payload.new_password)
    db.commit()

    logger.info("Password successfully changed for user: %s", target_username)

    # AUDIT
    try:
        actor_display = getattr(current_user, "username", "unknown")
        audit_change_both(
            scope="system",
            action="user_password_changed",
            actor=actor_display,
            extra={"username": target_username},
            db=db,
            actor_id=getattr(current_user, "id", None),
            actor_name=actor_display,
        )
    except Exception:
        pass

    return {"message": "Password changed successfully"}


@router.get("/admin/users", response_model=List[schemas.UserResponse])
def list_all_users(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    role = (current_user.profile.role or "").strip()
    if role not in ("Administrator", "Principal Investigator"):
        raise HTTPException(status_code=403, detail="Not allowed")
    users = db.query(models.User).all()
    return users


@router.post("/admin/users", response_model=schemas.UserResponse, status_code=status.HTTP_201_CREATED)
def admin_create_user(
    new: schemas.AdminUserCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.profile.role != "Administrator":
        raise HTTPException(status_code=403, detail="Not allowed")

    user = models.User(
        username=new.username,
        email=new.email,
        password=hash_password(new.password)
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    profile = models.UserProfile(
        user_id   = user.id,
        first_name= new.first_name,
        last_name = new.last_name,
        role      = new.role
    )
    db.add(profile)
    db.commit()
    db.refresh(profile)

    # AUDIT: new user created (admin)
    try:
        audit_change_both(
            scope="system",
            action="user_created_admin",
            actor=_display_name(current_user),
            extra={"target_user_id": user.id, "target_username": user.username, "role": profile.role},
            db=db,
            actor_id=current_user.id,
        )
    except Exception:
        pass

    return user


@router.patch("/admin/users/{user_id}/role", response_model=UserResponse)
def update_user_role(
    user_id: int,
    role_update: schemas.RoleUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    if current_user.profile.role != "Administrator":
        raise HTTPException(status_code=403, detail="Not allowed")

    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.profile.role = role_update.role
    db.commit()
    db.refresh(user)

    # AUDIT: admin changes roles
    try:
        audit_change_both(
            scope="system",
            action="admin_update_user_role",
            actor=_display_name(current_user),
            extra={"target_user_id": user.id, "target_username": user.username, "new_role": user.profile.role},
            db=db,
            actor_id=current_user.id,
        )
    except Exception:
        pass

    return user


@router.get("/{user_id}", response_model=UserResponse)
def get_user_by_id(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user
