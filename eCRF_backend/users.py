from datetime import timedelta, datetime, timezone
import jwt
import re
import secrets
from fastapi import APIRouter, Depends, HTTPException, Header, status
from fastapi.security import OAuth2PasswordBearer

from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel, Field

from . import schemas, models
from .schemas import LoginRequest, UserResponse, UserRegister
from .crud import get_user_by_username
from .auth import hash_password, verify_password, create_access_token, SECRET_KEY, ALGORITHM
from .database import get_db
from .logger import logger

# unified audit (DB + optional BIDS)
from .bids_exporter import audit_change_both
from .utils import local_now

# --------------------------------------------------------------------
# Inactivity / Session config
# --------------------------------------------------------------------
INACTIVITY_MINUTES = 30
ABSOLUTE_SESSION_HOURS = 24
LAST_ACTIVITY_THROTTLE_SECONDS = 30  # reduce DB writes

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


def _to_naive_utc(dt: Optional[datetime]) -> Optional[datetime]:
    """
    Normalize datetimes so comparisons never crash:
    - If dt is tz-aware => convert to UTC, then strip tzinfo (naive UTC)
    - If dt is naive => treat it as-is (already naive)
    This avoids "offset-naive vs offset-aware" TypeError.
    """
    if dt is None:
        return None
    if dt.tzinfo is not None and dt.utcoffset() is not None:
        return dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


def _revoke_session(db: Session, sess: models.UserSession) -> None:
    try:
        sess.revoked_at = local_now()
        db.commit()
    except Exception:
        db.rollback()


def get_current_user(
    authorization: str = Header(None),
    db: Session = Depends(get_db)
) -> models.User:
    """
    Header-based JWT decoding helper for protected endpoints (no audit).
    Enforces inactivity timeout using UserSession.last_activity_at.
    """
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header missing")
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authorization header must start with 'Bearer '")

    token = authorization.split("Bearer ")[1]
    try:
        # Decode without exp auto-check so we can keep behavior consistent with local_now()
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM],
            options={"verify_exp": False},
        )

        username = payload.get("sub")
        exp = payload.get("exp")
        jti = payload.get("jti")  # session id

        if not username or not exp:
            raise HTTPException(status_code=401, detail="Invalid token payload")

        # Normalize "now" for safe comparisons
        now_raw = local_now()
        now = _to_naive_utc(now_raw) or datetime.utcnow()

        # Absolute JWT expiry (cap) - compare timestamps (safe for naive/aware)
        if now_raw.timestamp() > float(exp):
            raise HTTPException(status_code=401, detail="Token expired")

        user = db.query(models.User).filter(models.User.username == username).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Backward compatibility: old tokens without jti governed only by exp.
        if not jti:
            logger.info("Authenticated user %s via legacy token (no jti).", user.username)
            return user

        sess = (
            db.query(models.UserSession)
            .filter(models.UserSession.jti == jti, models.UserSession.user_id == user.id)
            .first()
        )
        if not sess or sess.revoked_at is not None:
            raise HTTPException(status_code=401, detail="Session expired")

        # Normalize DB datetimes for safe comparisons
        abs_exp = _to_naive_utc(sess.absolute_expires_at)
        last_act = _to_naive_utc(sess.last_activity_at)
        created = _to_naive_utc(sess.created_at)

        # Absolute session cap (server-side)
        if abs_exp and now > abs_exp:
            _revoke_session(db, sess)
            raise HTTPException(status_code=401, detail="Session expired")

        # Inactivity timeout
        effective_last = last_act or created or now
        if (now - effective_last) > timedelta(minutes=INACTIVITY_MINUTES):
            _revoke_session(db, sess)
            raise HTTPException(status_code=401, detail="Session expired due to inactivity")

        # Update last activity (throttled) - use raw local_now() to preserve your existing storage style
        try:
            if (now - effective_last).total_seconds() > LAST_ACTIVITY_THROTTLE_SECONDS:
                sess.last_activity_at = now_raw
                db.commit()
        except Exception:
            db.rollback()
            # don't fail the request due to an activity write

        logger.info("User %s authenticated successfully.", user.username)
        return user

    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


@router.get("/me", response_model=UserResponse)
def get_current_user_oauth(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    """
    OAuth2PasswordBearer-based /me endpoint (no audit).
    Must enforce inactivity as well => reuse get_current_user.
    """
    return get_current_user(authorization=f"Bearer {token}", db=db)


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
    Returns token on success.
    Now creates a server-side session for inactivity enforcement.
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

    jti = secrets.token_urlsafe(32)

    now = local_now()
    sess = models.UserSession(
        user_id=user.id,
        jti=jti,
        last_activity_at=now,
        absolute_expires_at=now + timedelta(hours=ABSOLUTE_SESSION_HOURS),
    )
    db.add(sess)
    db.commit()

    token = create_access_token(user.username, jti=jti, max_age_hours=ABSOLUTE_SESSION_HOURS)
    logger.info("User %s logged in successfully.", request.username)
    return {"access_token": token, "token_type": "bearer"}


@router.post("/ping")
def ping(current_user: models.User = Depends(get_current_user)):
    """
    Optional: Frontend can call this periodically or on user interactions.
    It counts as activity and keeps the session alive.
    """
    return {"ok": True}

@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout_user(
    authorization: str = Header(None),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Best-effort logout:
    - Revokes the current server-side session row by jti.
    - If token is legacy (no jti), revoke all active sessions for that user (safest fallback).
    Always returns 204 (idempotent).
    """
    try:
        if not authorization or not authorization.startswith("Bearer "):
            return  # 204

        token = authorization.split("Bearer ")[1]
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM],
            options={"verify_exp": False},
        )
        jti = payload.get("jti")
        now = local_now()

        if jti:
            sess = (
                db.query(models.UserSession)
                .filter(
                    models.UserSession.user_id == current_user.id,
                    models.UserSession.jti == jti,
                    models.UserSession.revoked_at.is_(None),
                )
                .first()
            )
            if sess:
                sess.revoked_at = now
                db.commit()
            return  # 204

        # Legacy fallback: revoke all active sessions for this user
        sessions = (
            db.query(models.UserSession)
            .filter(
                models.UserSession.user_id == current_user.id,
                models.UserSession.revoked_at.is_(None),
            )
            .all()
        )
        if sessions:
            for s in sessions:
                s.revoked_at = now
            db.commit()

        return  # 204

    except Exception:
        db.rollback()
        return  # 204


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
        user_id=user.id,
        first_name=new.first_name,
        last_name=new.last_name,
        role=new.role
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
