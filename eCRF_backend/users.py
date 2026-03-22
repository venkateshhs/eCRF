from __future__ import annotations

from datetime import timedelta, datetime, timezone
import jwt
import re
import secrets

from fastapi import APIRouter, Depends, HTTPException, Header, status, Request
from fastapi.security import OAuth2PasswordBearer
from typing import List, Optional
from pydantic import BaseModel, Field

from . import schemas
from .schemas import LoginRequest, UserResponse, UserRegister
from .auth import hash_password, verify_password, create_access_token, SECRET_KEY, ALGORITHM
from .logger import logger
from .bids_exporter import audit_change_both
from .utils import local_now

from eCRF_backend.dts.crud_auth_dts import (
    list_users_from_dts,
    get_user_from_dts_by_username,
    get_user_from_dts_by_email,
    get_user_from_dts_by_id,
    next_user_id_from_dts,
    upsert_user_to_dts,
    get_session_from_dts,
    upsert_session_to_dts,
    revoke_session_in_dts,
    revoke_all_sessions_for_user_in_dts,
)

INACTIVITY_MINUTES = 30
ABSOLUTE_SESSION_HOURS = 24
LAST_ACTIVITY_THROTTLE_SECONDS = 30

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="users/login")

router = APIRouter(prefix="/users", tags=["users"])


def _display_name(u) -> str:
    if not u:
        return ""
    prof = getattr(u, "profile", None)
    first = getattr(prof, "first_name", "") or ""
    last = getattr(prof, "last_name", "") or ""
    full = (first + " " + last).strip()
    return full or getattr(u, "username", "") or getattr(u, "email", "") or f"User#{getattr(u, 'id', '')}"


def _to_naive_utc(dt: Optional[datetime]) -> Optional[datetime]:
    if dt is None:
        return None
    if dt.tzinfo is not None and dt.utcoffset() is not None:
        return dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


def _revoke_session(sess) -> None:
    try:
        revoke_session_in_dts(sess.jti, revoked_at=local_now())
    except Exception as e:
        logger.warning("Failed to revoke DTS session %s: %s", getattr(sess, "jti", None), e)


def get_current_user(
    authorization: str = Header(None),
) :
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header missing")
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authorization header must start with 'Bearer '")

    token = authorization.split("Bearer ")[1]
    try:
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM],
            options={"verify_exp": False},
        )

        username = payload.get("sub")
        exp = payload.get("exp")
        jti = payload.get("jti")

        if not username or not exp:
            raise HTTPException(status_code=401, detail="Invalid token payload")

        now_raw = local_now()
        now = _to_naive_utc(now_raw) or datetime.utcnow()

        if now_raw.timestamp() > float(exp):
            raise HTTPException(status_code=401, detail="Token expired")

        user = get_user_from_dts_by_username(username)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        if getattr(user, "status", "ACTIVE") not in {"ACTIVE"}:
            raise HTTPException(status_code=403, detail="User account is not active")

        if not jti:
            logger.info("Authenticated user %s via legacy token (no jti).", user.username)
            return user

        sess = get_session_from_dts(jti)
        if not sess or getattr(sess, "revoked_at", None) is not None:
            raise HTTPException(status_code=401, detail="Session expired")

        abs_exp = _to_naive_utc(sess.absolute_expires_at)
        last_act = _to_naive_utc(sess.last_activity_at)
        created = _to_naive_utc(sess.created_at)

        if abs_exp and now > abs_exp:
            _revoke_session(sess)
            raise HTTPException(status_code=401, detail="Session expired")

        effective_last = last_act or created or now
        if (now - effective_last) > timedelta(minutes=INACTIVITY_MINUTES):
            _revoke_session(sess)
            raise HTTPException(status_code=401, detail="Session expired due to inactivity")

        try:
            if (now - effective_last).total_seconds() > LAST_ACTIVITY_THROTTLE_SECONDS:
                upsert_session_to_dts(
                    user_id=sess.user_id,
                    username=sess.username or user.username,
                    jti=sess.jti,
                    created_at=sess.created_at,
                    last_activity_at=now_raw,
                    absolute_expires_at=sess.absolute_expires_at,
                    revoked_at=sess.revoked_at,
                    client_info=None,
                )
        except Exception as e:
            logger.warning("Failed to update last activity for session %s: %s", sess.jti, e)

        logger.info("User %s authenticated successfully.", user.username)
        return user

    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


@router.get("/me", response_model=UserResponse)
def get_current_user_oauth(
    token: str = Depends(oauth2_scheme),
):
    return get_current_user(authorization=f"Bearer {token}")


@router.post("/register", response_model=UserResponse)
def register_user(user_data: UserRegister):
    logger.info("Attempting to register a new DTS-backed user.")

    existing_user = get_user_from_dts_by_username(user_data.username)
    if existing_user:
        raise HTTPException(status_code=400, detail="Username already exists.")

    existing_email = get_user_from_dts_by_email(user_data.email)
    if existing_email:
        raise HTTPException(status_code=400, detail="Email already exists.")

    user_id = next_user_id_from_dts()
    hashed_password = hash_password(user_data.password)
    now = local_now()

    try:
        upsert_user_to_dts(
            user_id=user_id,
            username=user_data.username,
            email=user_data.email,
            password_hash=hashed_password,
            first_name=user_data.first_name,
            last_name=user_data.last_name,
            role="Investigator",
            status="ACTIVE",
            created_at=now,
            updated_at=now,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create DTS user: {e}")

    user = get_user_from_dts_by_id(user_id)
    if not user:
        raise HTTPException(status_code=500, detail="User creation succeeded but readback failed")

    try:
        audit_change_both(
            scope="system",
            action="user_created",
            actor=_display_name(user),
            extra={"username": user.username, "role": user.profile.role},
            db=None,
            actor_id=user.id,
        )
    except Exception:
        pass

    return user


@router.post("/login")
def login_user(request: LoginRequest, http_request: Request):
    logger.info("Login attempt for username: %s", request.username)

    user = get_user_from_dts_by_username(request.username)
    if not user or not verify_password(request.password, getattr(user, "password", "")):
        raise HTTPException(status_code=400, detail="Invalid username or password.")

    if user.profile and user.profile.role == "No Access":
        raise HTTPException(
            status_code=403,
            detail="Your account does not have permission to access this application.",
        )

    if getattr(user, "status", "ACTIVE") != "ACTIVE":
        raise HTTPException(status_code=403, detail="User account is not active")

    jti = secrets.token_urlsafe(32)
    now = local_now()

    client_info = {
        "client_host": http_request.client.host if http_request.client else None,
        "user_agent": http_request.headers.get("user-agent"),
    }

    try:
        upsert_session_to_dts(
            user_id=user.id,
            username=user.username,
            jti=jti,
            created_at=now,
            last_activity_at=now,
            absolute_expires_at=now + timedelta(hours=ABSOLUTE_SESSION_HOURS),
            revoked_at=None,
            client_info=client_info,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create DTS session: {e}")

    token = create_access_token(user.username, jti=jti, max_age_hours=ABSOLUTE_SESSION_HOURS)
    logger.info("User %s logged in successfully.", request.username)
    return {"access_token": token, "token_type": "bearer"}


@router.post("/ping")
def ping(current_user = Depends(get_current_user)):
    return {"ok": True}


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout_user(
    authorization: str = Header(None),
    current_user = Depends(get_current_user),
):
    try:
        if not authorization or not authorization.startswith("Bearer "):
            return

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
            revoke_session_in_dts(jti, revoked_at=now)
            return

        revoke_all_sessions_for_user_in_dts(current_user.id, revoked_at=now)
        return

    except Exception:
        return


class ChangePasswordRequest(BaseModel):
    new_password: str = Field(..., alias="new_password")
    username: Optional[str] = None


PASSWORD_RE = re.compile(r"^(?=.*[0-9])(?=.*[!@#$%^&*])[A-Za-z\d!@#$%^&*]{8,}$")


@router.post("/change-password")
def change_password(
    payload: ChangePasswordRequest,
    current_user = Depends(get_current_user),
):
    target_username = payload.username or getattr(current_user, "username", None)
    if not target_username:
        raise HTTPException(status_code=400, detail="Username resolution failed.")

    if not PASSWORD_RE.match(payload.new_password):
        raise HTTPException(
            status_code=400,
            detail="Password must be at least 8 characters, include a number, and a special character.",
        )

    is_admin = (getattr(current_user, "profile", None) and
                getattr(current_user.profile, "role", "") == "Administrator")
    if payload.username and not is_admin and payload.username != current_user.username:
        raise HTTPException(status_code=403, detail="Not authorized to change another user's password.")

    user = get_user_from_dts_by_username(target_username)
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    now = local_now()

    try:
        upsert_user_to_dts(
            user_id=user.id,
            username=user.username,
            email=user.email,
            password_hash=hash_password(payload.new_password),
            first_name=user.profile.first_name,
            last_name=user.profile.last_name,
            role=user.profile.role,
            status=getattr(user, "status", "ACTIVE"),
            created_at=user.created_at or now,
            updated_at=now,
        )
        revoke_all_sessions_for_user_in_dts(user.id, revoked_at=now)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update DTS password: {e}")

    logger.info("Password successfully changed for user: %s", target_username)

    try:
        actor_display = getattr(current_user, "username", "unknown")
        audit_change_both(
            scope="system",
            action="user_password_changed",
            actor=actor_display,
            extra={"username": target_username},
            db=None,
            actor_id=getattr(current_user, "id", None),
            actor_name=actor_display,
        )
    except Exception:
        pass

    return {"message": "Password changed successfully"}


@router.get("/admin/users", response_model=List[schemas.UserResponse])
def list_all_users(
    current_user = Depends(get_current_user),
):
    role = (current_user.profile.role or "").strip()
    if role not in ("Administrator", "Principal Investigator"):
        raise HTTPException(status_code=403, detail="Not allowed")

    users = []
    for u in list_users_from_dts():
        users.append(get_user_from_dts_by_id(u["id"]))
    return [u for u in users if u is not None]


@router.post("/admin/users", response_model=schemas.UserResponse, status_code=status.HTTP_201_CREATED)
def admin_create_user(
    new: schemas.AdminUserCreate,
    current_user = Depends(get_current_user),
):
    if current_user.profile.role != "Administrator":
        raise HTTPException(status_code=403, detail="Not allowed")

    if get_user_from_dts_by_username(new.username):
        raise HTTPException(status_code=400, detail="Username already exists.")
    if get_user_from_dts_by_email(new.email):
        raise HTTPException(status_code=400, detail="Email already exists.")

    user_id = next_user_id_from_dts()
    now = local_now()

    try:
        upsert_user_to_dts(
            user_id=user_id,
            username=new.username,
            email=new.email,
            password_hash=hash_password(new.password),
            first_name=new.first_name,
            last_name=new.last_name,
            role=new.role,
            status="ACTIVE",
            created_at=now,
            updated_at=now,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create DTS user: {e}")

    user = get_user_from_dts_by_id(user_id)
    if not user:
        raise HTTPException(status_code=500, detail="User creation succeeded but readback failed")

    try:
        audit_change_both(
            scope="system",
            action="user_created_admin",
            actor=_display_name(current_user),
            extra={"target_user_id": user.id, "target_username": user.username, "role": user.profile.role},
            db=None,
            actor_id=current_user.id,
        )
    except Exception:
        pass

    return user


@router.patch("/admin/users/{user_id}/role", response_model=UserResponse)
def update_user_role(
    user_id: int,
    role_update: schemas.RoleUpdate,
    current_user = Depends(get_current_user),
):
    if current_user.profile.role != "Administrator":
        raise HTTPException(status_code=403, detail="Not allowed")

    user = get_user_from_dts_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    now = local_now()

    try:
        upsert_user_to_dts(
            user_id=user.id,
            username=user.username,
            email=user.email,
            password_hash=user.password,
            first_name=user.profile.first_name,
            last_name=user.profile.last_name,
            role=role_update.role,
            status=getattr(user, "status", "ACTIVE"),
            created_at=user.created_at or now,
            updated_at=now,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update DTS user role: {e}")

    updated = get_user_from_dts_by_id(user_id)
    if not updated:
        raise HTTPException(status_code=500, detail="Role update succeeded but readback failed")

    try:
        audit_change_both(
            scope="system",
            action="admin_update_user_role",
            actor=_display_name(current_user),
            extra={"target_user_id": updated.id, "target_username": updated.username, "new_role": updated.profile.role},
            db=None,
            actor_id=current_user.id,
        )
    except Exception:
        pass

    return updated


@router.get("/{user_id}", response_model=UserResponse)
def get_user_by_id(
    user_id: int,
    current_user = Depends(get_current_user),
):
    user = get_user_from_dts_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user