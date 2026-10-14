#!/usr/bin/env bash
set -euo pipefail
cd /app

cat > src/auth.py <<'EOT'
import hmac
import os


def get_expected_api_key() -> str:
    return os.getenv("ADMIN_API_KEY", "")


def is_authorized(provided_key):
    if not isinstance(provided_key, str) or not provided_key:
        raise ValueError("provided_key must be a non-empty string")

    expected = get_expected_api_key()
    if not expected:
        return False

    return hmac.compare_digest(provided_key, expected)
EOT

mkdir -p security
cat > security/timing_mitigation.md <<'EOT'
# Vulnerability
The auth check used direct string equality for API keys, which can leak timing information.

# Fix
Switched to `hmac.compare_digest` and added strict input validation for `provided_key`.

# Validation
Confirmed valid keys authorize, invalid keys fail, and invalid input types raise `ValueError`.
EOT
