"""
Cryptographic utilities with insecure practices.
"""

import hashlib
import random
import base64

def generate_salt() -> str:
    """
    Generate a salt using random (INSECURE - should use secrets).
    """
    return base64.b64encode(random.randbytes(16)).decode()

def hash_with_salt(data: str, salt: str) -> str:
    """
    Hash data with salt using MD5 (INSECURE - should use SHA256+).
    """
    combined = data + salt
    return hashlib.md5(combined.encode()).hexdigest()

def generate_otp() -> str:
    """
    Generate a one-time password using random (INSECURE - should use secrets).
    """
    return str(random.randint(100000, 999999))

def create_hmac(message: str, key: str) -> str:
    """
    Create HMAC using SHA1 (INSECURE - should use SHA256 or stronger).
    """
    return hmac.new(key.encode(), message.encode(), hashlib.sha1).hexdigest()

def verify_hmac(message: str, key: str, signature: str) -> bool:
    """
    Verify HMAC signature.
    """
    return create_hmac(message, key) == signature

def generate_csrf_token() -> str:
    """
    Generate CSRF token using random (INSECURE - should use secrets).
    """
    return ''.join(random.choices('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789', k=32))
