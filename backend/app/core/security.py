from datetime import datetime, timedelta, timezone
import base64
import secrets
import jwt
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from pwdlib import PasswordHash
from .config import get_settings

password_hash = PasswordHash.recommended()
def hash_password(password: str) -> str: return password_hash.hash(password)
def verify_password(password: str, hashed: str) -> bool: return password_hash.verify(password, hashed)
def create_refresh_token() -> str: return secrets.token_urlsafe(48)

# Refresh-token rotation stores the successor token sealed under a key
# derived from the PREDECESSOR's raw value, so the row can hand the same
# successor back to a client that retries with the predecessor (lost
# response, second tab) without the database ever holding a usable token:
# only the token's SHA-256 digest is stored, so a database reader cannot
# derive the key. The predecessor's digest is bound in as associated data.
_SUCCESSOR_INFO = b"lingosquared/refresh-token-successor/v1"


def _successor_key(previous_raw: str) -> bytes:
    return HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=None,
        info=_SUCCESSOR_INFO,
    ).derive(previous_raw.encode("utf-8"))


def seal_successor_token(previous_raw: str, previous_digest: str, successor_raw: str) -> str:
    nonce = secrets.token_bytes(12)
    ciphertext = AESGCM(_successor_key(previous_raw)).encrypt(
        nonce, successor_raw.encode("utf-8"), previous_digest.encode("ascii")
    )
    return base64.urlsafe_b64encode(nonce + ciphertext).decode("ascii")


def open_successor_token(previous_raw: str, previous_digest: str, sealed: str) -> str | None:
    try:
        blob = base64.urlsafe_b64decode(sealed.encode("ascii"))
        plaintext = AESGCM(_successor_key(previous_raw)).decrypt(
            blob[:12], blob[12:], previous_digest.encode("ascii")
        )
    except Exception:
        return None
    return plaintext.decode("utf-8")
def create_token(user_id: str) -> str:
    s = get_settings(); now = datetime.now(timezone.utc)
    return jwt.encode({"sub": user_id, "jti": secrets.token_urlsafe(8), "iat": now, "exp": now + timedelta(seconds=s.access_token_expire_seconds)}, s.jwt_secret, algorithm="HS256")
def decode_token(token: str) -> str:
    return jwt.decode(token, get_settings().jwt_secret, algorithms=["HS256"])["sub"]
