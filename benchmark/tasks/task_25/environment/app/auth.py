"""
auth.py — Simple token-based authentication module.
BUG: validate_token() does not check token expiry.
"""
import hashlib
import time
from typing import Optional

# In-memory token store: {token: {"user": str, "expires_at": float}}
_token_store: dict = {}


def generate_token(username: str, ttl_seconds: int = 3600) -> str:
    """Generate a new auth token for a user."""
    raw = f"{username}:{time.time()}:{ttl_seconds}"
    token = hashlib.sha256(raw.encode()).hexdigest()
    _token_store[token] = {
        "user": username,
        "expires_at": time.time() + ttl_seconds,
    }
    return token


def validate_token(token: str) -> Optional[str]:
    """
    Return the username if the token is valid, else None.
    BUG: does not check whether the token has expired.
    """
    record = _token_store.get(token)
    if record is None:
        return None
    # BUG: missing expiry check — expired tokens are accepted forever
    return record["user"]


def revoke_token(token: str) -> bool:
    """Revoke a token. Returns True if it existed."""
    if token in _token_store:
        del _token_store[token]
        return True
    return False


def get_token_info(token: str) -> Optional[dict]:
    """Return token metadata or None if not found."""
    return _token_store.get(token)
