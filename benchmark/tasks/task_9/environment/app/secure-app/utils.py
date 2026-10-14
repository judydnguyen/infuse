"""
Utility functions with some insecure random usage.
"""

import random
import hashlib

def generate_id() -> str:
    """
    Generate a unique ID using random (OK for non-security use).
    """
    return ''.join(random.choices('0123456789abcdef', k=16))

def hash_data(data: str) -> str:
    """
    Hash data using SHA1 (INSECURE - should use SHA256 or stronger).
    """
    return hashlib.sha1(data.encode()).hexdigest()

def generate_verification_code() -> str:
    """
    Generate verification code using random (INSECURE - should use secrets for security).
    """
    return str(random.randint(1000, 9999))

def create_checksum(data: bytes) -> str:
    """
    Create checksum using MD5 (INSECURE - should use SHA256 for security).
    """
    return hashlib.md5(data).hexdigest()

def shuffle_list(items: list) -> list:
    """
    Shuffle a list using random (OK for non-security use).
    """
    shuffled = items.copy()
    random.shuffle(shuffled)
    return shuffled
