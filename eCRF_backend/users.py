from datetime import timedelta, datetime, timezone
import jwt
import ipaddress
import re
import secrets
from fastapi import APIRouter, Depends, HTTPException, Header, Query, Request, status
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
from .password_reset import (
    build_reset_url,
    mask_email,
    new_token,
    send_password_reset_email,
    token_hash,
)
from .settings import get_settings

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
settings = get_settings()


def _display_name(u: Optional[models.User]) -> str:
    if not u:
        return ""
    prof = getattr(u, "profile", None)
    first = getattr(prof, "first_name", "") or ""
    last = getattr(prof, "last_name", "") or ""
    full = (first + " " + last).strip()
    return full or u.username or u.email or f"User#{u.id}"


def _get_user_password_hash(user: Optional[models.User]) -> str:
    if not user:
        return ""
    return (
        getattr(user, "password_hash", None)
        or getattr(user, "password", None)
        or ""
    )


def _set_user_password_hash(user: models.User, hashed_password: str) -> None:
    if hasattr(user, "password_hash"):
        setattr(user, "password_hash", hashed_password)
    elif hasattr(user, "password"):
        setattr(user, "password", hashed_password)
    else:
        raise AttributeError("User model has neither 'password_hash' nor 'password'")


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
    request: Request = None,
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

        if not jti:
            raise HTTPException(status_code=401, detail="Session expired")

        sess = (
            db.query(models.UserSession)
            .filter(models.UserSession.jti == jti, models.UserSession.user_id == user.id)
            .first()
        )
        if not sess or sess.revoked_at is not None:
            raise HTTPException(status_code=401, detail="Session expired")

        if getattr(user, "must_change_password", False):
            allowed_paths = {
                "/users/me",
                "/users/change-password",
                "/users/logout",
                "/users/ping",
            }
            request_path = request.url.path if request else ""
            if request_path and request_path not in allowed_paths:
                raise HTTPException(
                    status_code=403,
                    detail="Password change required before continuing.",
                )

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

        # Update last activity (throttled)
        try:
            if (now - effective_last).total_seconds() > LAST_ACTIVITY_THROTTLE_SECONDS:
                sess.last_activity_at = now_raw
                db.commit()
        except Exception:
            db.rollback()

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

    existing_user = db.query(models.User).filter(
        (models.User.username == user_data.username) | (models.User.email == user_data.email)
    ).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Username or email already exists.")

    hashed_password = hash_password(user_data.password)

    user = models.User(
        username=user_data.username,
        email=user_data.email,
    )
    _set_user_password_hash(user, hashed_password)

    db.add(user)
    db.commit()
    db.refresh(user)

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
    Creates a server-side session for inactivity enforcement.
    """
    logger.info("Login attempt for username: %s", request.username)

    user = get_user_by_username(db, request.username)
    if not user or not verify_password(request.password, _get_user_password_hash(user)):
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

    token = create_access_token(
        {
            "sub": user.username,
            "jti": jti,
        },
        expires_delta=timedelta(hours=ABSOLUTE_SESSION_HOURS),
    )

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
    Always returns 204 (idempotent).
    """
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

        return

    except Exception:
        db.rollback()
        return


class ChangePasswordRequest(BaseModel):
    new_password: str = Field(..., alias="new_password")
    username: Optional[str] = None


PASSWORD_RE = re.compile(r"^(?=.*[0-9])(?=.*[!@#$%^&*])\S{8,}$")


class PasswordResetLookupRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=50)


class PasswordResetLookupResponse(BaseModel):
    eligible: bool
    masked_email: Optional[str] = None
    confirmation_token: Optional[str] = None


class PasswordResetEmailRequest(BaseModel):
    confirmation_token: str = Field(..., min_length=20, max_length=200)


class PasswordResetConfirmRequest(BaseModel):
    token: str = Field(..., min_length=20, max_length=200)
    new_password: str


class PasswordResetTokenInfoResponse(BaseModel):
    username: str


def _request_ip(request: Request) -> str:
    if settings.trust_proxy_headers:
        forwarded_for = request.headers.get("x-forwarded-for", "")
        # Apache appends the peer it observed to the right-hand side. Using the
        # last valid value avoids trusting a client-prepended address.
        for candidate in reversed(forwarded_for.split(",")):
            candidate = candidate.strip()
            try:
                return str(ipaddress.ip_address(candidate))
            except ValueError:
                continue
    return request.client.host if request.client else "unknown"


def _valid_reset_token(row: Optional[models.PasswordResetToken], now: datetime) -> bool:
    if not row or row.used_at is not None:
        return False
    expires_at = _to_naive_utc(row.expires_at)
    current = _to_naive_utc(now) or datetime.utcnow()
    return bool(expires_at and expires_at >= current)


def _create_reset_token_row(
    *,
    db: Session,
    user_id: Optional[int],
    purpose: str,
    requested_ip: str,
    ttl_minutes: int,
) -> tuple[str, models.PasswordResetToken]:
    raw_token = new_token()
    now = local_now()
    row = models.PasswordResetToken(
        user_id=user_id,
        purpose=purpose,
        token_hash=token_hash(raw_token),
        requested_ip=requested_ip,
        created_at=now,
        expires_at=now + timedelta(minutes=ttl_minutes),
    )
    db.add(row)
    return raw_token, row


def _require_password_reset_enabled() -> None:
    if not settings.password_reset_enabled:
        raise HTTPException(status_code=503, detail="Password reset is not configured.")


@router.post("/password-reset/lookup", response_model=PasswordResetLookupResponse)
def password_reset_lookup(
    payload: PasswordResetLookupRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """Resolve a username and return only a masked delivery-address hint."""
    _require_password_reset_enabled()
    now = local_now()
    requested_ip = _request_ip(request)
    cutoff = now - timedelta(hours=1)
    lookup_count = (
        db.query(models.PasswordResetToken)
        .filter(
            models.PasswordResetToken.requested_ip == requested_ip,
            models.PasswordResetToken.purpose.in_(("email_confirmation", "lookup_unknown")),
            models.PasswordResetToken.created_at >= cutoff,
        )
        .count()
    )
    if lookup_count >= settings.password_reset_max_lookups_per_ip_hour:
        raise HTTPException(status_code=429, detail="Too many password reset attempts. Try again later.")

    username = payload.username.strip()
    user = get_user_by_username(db, username)
    if not user or not getattr(user, "email", None):
        _create_reset_token_row(
            db=db,
            user_id=None,
            purpose="lookup_unknown",
            requested_ip=requested_ip,
            ttl_minutes=settings.password_reset_confirmation_ttl_minutes,
        )
        db.commit()
        return PasswordResetLookupResponse(eligible=False)

    confirmation_token, _ = _create_reset_token_row(
        db=db,
        user_id=user.id,
        purpose="email_confirmation",
        requested_ip=requested_ip,
        ttl_minutes=settings.password_reset_confirmation_ttl_minutes,
    )
    db.commit()
    return PasswordResetLookupResponse(
        eligible=True,
        masked_email=mask_email(user.email),
        confirmation_token=confirmation_token,
    )


@router.post("/password-reset/request")
def password_reset_request_email(
    payload: PasswordResetEmailRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """Consume an address confirmation and email a one-time password-reset link."""
    _require_password_reset_enabled()
    now = local_now()
    confirmation = (
        db.query(models.PasswordResetToken)
        .filter(
            models.PasswordResetToken.token_hash == token_hash(payload.confirmation_token),
            models.PasswordResetToken.purpose == "email_confirmation",
        )
        .first()
    )
    if not _valid_reset_token(confirmation, now) or not confirmation.user:
        raise HTTPException(status_code=400, detail="This confirmation has expired. Start again.")

    cutoff = now - timedelta(hours=1)
    sent_count = (
        db.query(models.PasswordResetToken)
        .filter(
            models.PasswordResetToken.user_id == confirmation.user_id,
            models.PasswordResetToken.purpose == "password_reset",
            models.PasswordResetToken.created_at >= cutoff,
        )
        .count()
    )
    if sent_count >= settings.password_reset_max_per_user_hour:
        raise HTTPException(status_code=429, detail="Too many reset emails. Try again later.")

    confirmation.used_at = now
    db.query(models.PasswordResetToken).filter(
        models.PasswordResetToken.user_id == confirmation.user_id,
        models.PasswordResetToken.purpose == "password_reset",
        models.PasswordResetToken.used_at.is_(None),
    ).update({"used_at": now}, synchronize_session=False)

    raw_token, reset_row = _create_reset_token_row(
        db=db,
        user_id=confirmation.user_id,
        purpose="password_reset",
        requested_ip=_request_ip(request),
        ttl_minutes=settings.password_reset_ttl_minutes,
    )
    db.commit()

    try:
        send_password_reset_email(
            recipient=confirmation.user.email,
            username=confirmation.user.username,
            reset_url=build_reset_url(raw_token),
        )
    except Exception:
        logger.exception("Password reset email delivery failed for user_id=%s", confirmation.user_id)
        reset_row.used_at = local_now()
        db.commit()
        raise HTTPException(status_code=503, detail="The reset email could not be sent. Try again later.")

    logger.info("Password reset email sent for user_id=%s", confirmation.user_id)
    return {"message": "Password reset email sent."}


@router.post("/password-reset/confirm")
def password_reset_confirm(
    payload: PasswordResetConfirmRequest,
    db: Session = Depends(get_db),
):
    """Consume a reset token, update the password, and revoke existing sessions."""
    _require_password_reset_enabled()
    if not PASSWORD_RE.match(payload.new_password):
        raise HTTPException(
            status_code=400,
            detail="Password must be at least 8 characters, include a number, and a special character.",
        )

    now = local_now()
    reset_row = (
        db.query(models.PasswordResetToken)
        .filter(
            models.PasswordResetToken.token_hash == token_hash(payload.token),
            models.PasswordResetToken.purpose == "password_reset",
        )
        .first()
    )
    if not _valid_reset_token(reset_row, now) or not reset_row.user:
        raise HTTPException(status_code=400, detail="This password reset link is invalid or expired.")

    user = reset_row.user
    _set_user_password_hash(user, hash_password(payload.new_password))
    user.must_change_password = False
    reset_row.used_at = now
    db.query(models.PasswordResetToken).filter(
        models.PasswordResetToken.user_id == user.id,
        models.PasswordResetToken.used_at.is_(None),
    ).update({"used_at": now}, synchronize_session=False)
    db.query(models.UserSession).filter(
        models.UserSession.user_id == user.id,
        models.UserSession.revoked_at.is_(None),
    ).update({"revoked_at": now}, synchronize_session=False)
    db.commit()

    try:
        audit_change_both(
            scope="system",
            action="user_password_reset",
            actor=user.username,
            extra={"username": user.username, "method": "email_reset"},
            db=db,
            actor_id=user.id,
            actor_name=user.username,
        )
    except Exception:
        pass

    logger.info("Password reset completed for user_id=%s", user.id)
    return {"message": "Password reset successfully."}


@router.get("/password-reset/validate", response_model=PasswordResetTokenInfoResponse)
def password_reset_validate(
    token: str = Query(..., min_length=20, max_length=200),
    db: Session = Depends(get_db),
):
    """Validate a reset link and return the account name shown on the reset page."""
    _require_password_reset_enabled()
    reset_row = (
        db.query(models.PasswordResetToken)
        .filter(
            models.PasswordResetToken.token_hash == token_hash(token),
            models.PasswordResetToken.purpose == "password_reset",
        )
        .first()
    )
    if not _valid_reset_token(reset_row, local_now()) or not reset_row.user:
        raise HTTPException(status_code=400, detail="This password reset link is invalid or expired.")
    return PasswordResetTokenInfoResponse(username=reset_row.user.username)


@router.post("/change-password")
def change_password(
    payload: ChangePasswordRequest,
    authorization: str = Header(None),
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

    is_admin = (
        getattr(current_user, "profile", None)
        and getattr(current_user.profile, "role", "") == "Administrator"
    )
    if payload.username and not is_admin and payload.username != current_user.username:
        raise HTTPException(status_code=403, detail="Not authorized to change another user's password.")

    user = get_user_by_username(db, target_username)
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    _set_user_password_hash(user, hash_password(payload.new_password))
    is_self_change = user.id == current_user.id
    user.must_change_password = False if is_self_change else True

    current_jti = None
    if authorization and authorization.startswith("Bearer "):
        try:
            token = authorization.split("Bearer ")[1]
            current_jti = jwt.decode(
                token,
                SECRET_KEY,
                algorithms=[ALGORITHM],
                options={"verify_exp": False},
            ).get("jti")
        except Exception:
            current_jti = None

    session_query = db.query(models.UserSession).filter(
        models.UserSession.user_id == user.id,
        models.UserSession.revoked_at.is_(None),
    )
    if is_self_change and current_jti:
        session_query = session_query.filter(models.UserSession.jti != current_jti)
    session_query.update({"revoked_at": local_now()}, synchronize_session=False)
    db.commit()

    logger.info("Password successfully changed for user: %s", target_username)

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
    )
    _set_user_password_hash(user, hash_password(new.password))

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
