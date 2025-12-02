import bcrypt
import jwt
from datetime import datetime, timedelta
from fastapi import Request, HTTPException, status, Depends

from .utils import local_now

SECRET_KEY = "your-very-secure-secret-key"
ALGORITHM = "HS256"
USE_ENCRYPTION = True  # Toggle encryption

def hash_password(password: str) -> str:
    if USE_ENCRYPTION:
        return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    return password

def verify_password(password: str, hashed_password: str) -> bool:
    if USE_ENCRYPTION:
        return bcrypt.checkpw(password.encode("utf-8"), hashed_password.encode("utf-8"))
    return password == hashed_password

def create_access_token(username: str) -> str:
    expire = local_now() + timedelta(minutes=30)
    payload = {"sub": username, "exp": int(expire.timestamp())}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def extract_token(request: Request) -> str:
    """
    Extracts the token from the Authorization header.
    """
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No access token found. Please log in.",
        )
    try:
        scheme, token = auth_header.split()
        if scheme.lower() != "bearer":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication scheme. Expected Bearer token.",
            )
        return token
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Authorization header format.",
        )


