import bcrypt
import jwt
from datetime import datetime, timedelta

# Configuration: Toggle encryption on or off
USE_ENCRYPTION = True  # Set to False to disable encryption

SECRET_KEY = "your-very-secure-secret-key"
ALGORITHM = "HS256"

def hash_password(password: str) -> str:
    if USE_ENCRYPTION:
        return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    return password  # Return the password as-is if encryption is disabled

def verify_password(password: str, hashed_password: str) -> bool:
    if USE_ENCRYPTION:
        return bcrypt.checkpw(password.encode("utf-8"), hashed_password.encode("utf-8"))
    return password == hashed_password  # Compare directly if encryption is disabled

def create_access_token(username: str) -> str:
    expire = datetime.utcnow() + timedelta(minutes=30)  # Token expiry time
    payload = {"sub": username, "exp": expire}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
