#!/usr/bin/env python3
"""
Main application entry point.
"""

from auth import hash_password, generate_session_token, generate_api_key
from crypto import generate_otp, generate_csrf_token, create_hmac
from utils import generate_verification_code, hash_data

def main():
    """Main function demonstrating insecure crypto usage."""
    # Insecure password hashing
    password = "user123"
    password_hash = hash_password(password)
    print(f"Password hash (MD5): {password_hash}")
    
    # Insecure session token generation
    token = generate_session_token()
    print(f"Session token: {token}")
    
    # Insecure API key generation
    api_key = generate_api_key()
    print(f"API key: {api_key}")
    
    # Insecure OTP generation
    otp = generate_otp()
    print(f"OTP: {otp}")
    
    # Insecure CSRF token
    csrf = generate_csrf_token()
    print(f"CSRF token: {csrf}")
    
    # Insecure verification code
    code = generate_verification_code()
    print(f"Verification code: {code}")
    
    # Insecure data hashing
    data_hash = hash_data("sensitive data")
    print(f"Data hash (SHA1): {data_hash}")
    
    # Insecure HMAC
    hmac_signature = create_hmac("message", "secret_key")
    print(f"HMAC (SHA1): {hmac_signature}")

if __name__ == "__main__":
    main()
