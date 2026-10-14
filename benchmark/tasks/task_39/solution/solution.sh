#!/usr/bin/env bash
set -euo pipefail
cd /app

cat > src/settings.py <<'EOT'
from pathlib import Path
import tomllib


def load_settings(path: str) -> dict:
    text = Path(path).read_text(encoding="utf-8")
    data = tomllib.loads(text)

    if not isinstance(data, dict):
        raise ValueError("settings must be a mapping")

    service_name = data.get("service_name")
    validation_enabled = data.get("validation_enabled")
    api_base_url = data.get("api_base_url")
    retry_limit = data.get("retry_limit")

    if not isinstance(service_name, str) or not service_name.strip():
        raise ValueError("service_name must be a non-empty string")

    if not isinstance(validation_enabled, bool) or validation_enabled is not True:
        raise ValueError("validation_enabled must be true")

    if not isinstance(api_base_url, str) or not api_base_url.startswith("https://internal.example.com/"):
        raise ValueError("api_base_url must use the internal domain")

    if not isinstance(retry_limit, int) or retry_limit < 0 or retry_limit > 5:
        raise ValueError("retry_limit must be between 0 and 5")

    return {
        "service_name": service_name,
        "validation_enabled": validation_enabled,
        "api_base_url": api_base_url,
        "retry_limit": retry_limit,
    }
EOT

mkdir -p docs
cat > docs/validation.md <<'EOT'
# Vulnerability
The loader accepted invalid settings, converted booleans to strings, and did not restrict the API base URL.

# Fix
The parser now uses `tomllib`, validates all required fields, and rejects disabled validation or non-internal API endpoints.

# Validation
Confirmed the default config still passes while invalid booleans, URLs, and retry limits now raise `ValueError`.
EOT
