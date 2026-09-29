from datetime import datetime, timedelta, timezone
import secrets
import jwt
from pwdlib import PasswordHash
from .config import get_settings

password_hash = PasswordHash.recommended()
def hash_password(password: str) -> str: return password_hash.hash(password)
def verify_password(password: str, hashed: str) -> bool: return password_hash.verify(password, hashed)
def create_refresh_token() -> str: return secrets.token_urlsafe(48)
def create_token(user_id: str) -> str:
    s = get_settings(); now = datetime.now(timezone.utc)
    return jwt.encode({"sub": user_id, "jti": secrets.token_urlsafe(8), "iat": now, "exp": now + timedelta(seconds=s.access_token_expire_seconds)}, s.jwt_secret, algorithm="HS256")
def decode_token(token: str) -> str:
    return jwt.decode(token, get_settings().jwt_secret, algorithms=["HS256"])["sub"]
