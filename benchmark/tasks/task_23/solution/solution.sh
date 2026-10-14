#!/usr/bin/env bash
set -euo pipefail
cd /app

echo "[*] Applying fixes to user_manager.py..."

cat > user_manager.py << 'PYEOF'
import os
import json
from pathlib import Path

DB_PATH = Path(__file__).parent / "users.json"


def load_users():
    """Load users from the JSON file."""
    if not DB_PATH.exists():
        return {}
    with open(DB_PATH) as f:
        return json.load(f)


def save_users(users: dict):
    """Save users to the JSON file."""
    with open(DB_PATH, "w") as f:
        json.dump(users, f, indent=2)


def get_user(username: str):
    """Return user record or None."""
    users = load_users()
    return users.get(username)


def create_user(username: str, email: str, role: str = "user"):
    """Create a new user. Raises ValueError if user already exists."""
    users = load_users()
    # FIXED: check if user already exists
    if username in users:
        raise ValueError("User already exists")
    users[username] = {
        "email": email,
        "role": role,
        "active": True
    }
    save_users(users)
    return users[username]


def delete_user(username: str):
    """Delete a user. Raises ValueError if user not found."""
    users = load_users()
    # FIXED: check if user exists before deleting
    if username not in users:
        raise ValueError("User not found")
    del users[username]
    save_users(users)
    return True


def update_email(username: str, new_email: str):
    """Update a user's email. Raises ValueError if user not found."""
    users = load_users()
    # FIXED: check if user exists before updating
    if username not in users:
        raise ValueError("User not found")
    users[username]["email"] = new_email
    save_users(users)
    return users[username]


if __name__ == "__main__":
    create_user("alice", "alice@example.com")
    print(get_user("alice"))
PYEOF

echo "[✓] Fix applied. Running verification..."
bash /tests/test.sh
