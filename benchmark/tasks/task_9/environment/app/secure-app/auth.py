"""
Authentication module with insecure cryptographic practices.
"""

import hashlib
import random
import hmac

def hash_password(password: str) -> str:
    """
    Hash a password using MD5 (INSECURE - should use bcrypt or argon2).
    """
    return hashlib.md5(password.encode()).hexdigest()

def verify_password(password: str, password_hash: str) -> bool:
    """
    Verify a password against a hash.
    """
    return hash_password(password) == password_hash

def generate_session_token() -> str:
    """
    Generate a session token using random (INSECURE - should use secrets).
    """
    return ''.join(random.choices('abcdefghijklmnopqrstuvwxyz0123456789', k=32))

def generate_api_key() -> str:
    """
    Generate an API key using random (INSECURE - should use secrets).
    """
    return ''.join(random.choices('ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789', k=40))

def hash_file(file_path: str) -> str:
    """
    Hash a file using SHA1 (INSECURE - should use SHA256 or stronger).
    """
    sha1 = hashlib.sha1()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b''):
            sha1.update(chunk)
    return sha1.hexdigest()

def verify_file_integrity(file_path: str, expected_hash: str) -> bool:
    """
    Verify file integrity using SHA1.
    """
    return hash_file(file_path) == expected_hash
