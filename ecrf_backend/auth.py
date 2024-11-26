import bcrypt
import jwt
from datetime import datetime, timedelta

SECRET_KEY = "your-very-secure-secret-key"

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

def verify_password(password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), hashed_password.encode("utf-8"))

def create_access_token(username: str):
    expiry = datetime.utcnow() + timedelta(hours=1)
    payload = {"sub": username, "exp": expiry}
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")
