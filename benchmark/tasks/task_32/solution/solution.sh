#!/usr/bin/env bash
set -euo pipefail
cd /app

echo "[*] Applying fix to api_client.py..."

cat > api_client.py << 'PYEOF'
"""API client module."""
import json
import os


def load_api_config(path):
    if not os.path.exists(path):
        raise ValueError(f"API config file not found: {path}")
    with open(path, "r") as f:
        return json.load(f)


def get_endpoint(config, name):
    # FIXED: handle missing endpoint
    if name not in config["endpoints"]:
        raise ValueError(f"Endpoint not found: {name}")
    return config["endpoints"][name]


def validate_response(response):
    # FIXED: handle missing status field
    if "status" not in response:
        raise ValueError("Response missing status field")
    status = response["status"]
    if status not in ["success", "error"]:
        raise ValueError(f"Invalid status: {status}")
    return status


def build_request(endpoint, method, payload=None):
    request = {
        "url": endpoint["url"],
        "method": method,
        "headers": endpoint.get("headers", {}),
    }
    if payload:
        request["payload"] = payload
    return request


if __name__ == "__main__":
    config = load_api_config("api_config.json")
    endpoint = get_endpoint(config, "users")
    print(endpoint)
PYEOF

echo "[✓] Fix applied. Running verification..."
bash /tests/test.sh
