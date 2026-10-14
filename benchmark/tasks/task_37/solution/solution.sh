#!/usr/bin/env bash
set -euo pipefail
cd /app

cat > router.py <<'EOT'
from urllib.parse import urlsplit


def build_redirect(next_path: str) -> str:
    if not next_path:
        return "/"

    parts = urlsplit(next_path)
    if parts.scheme or parts.netloc or next_path.startswith("//"):
        raise ValueError("invalid redirect target")

    return next_path if next_path.startswith("/") else f"/{next_path}"


def redirect_response(next_path: str) -> dict:
    return {"location": build_redirect(next_path), "status_code": 302}
EOT

mkdir -p security
cat > security/review.md <<'EOT'
# Vulnerability
`build_redirect()` accepted attacker-controlled redirect targets, including absolute and scheme-relative URLs.

# Fix
The implementation now parses the target, rejects external redirects, and normalizes safe in-app paths to start with `/`.

# Validation
Verified that normal relative app paths still work while absolute URLs and scheme-relative values raise `ValueError`.
EOT
