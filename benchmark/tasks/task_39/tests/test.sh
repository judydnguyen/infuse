#!/usr/bin/env bash
set -euo pipefail
cd /app

echo "[*] Running settings validation tests..."

required_files=(
  "README.md"
  "config/settings.toml"
  "scripts/deploy_check.sh"
  "src/settings.py"
  "src/main.py"
  "docs/validation.md"
)

for f in "${required_files[@]}"; do
  if [ ! -f "$f" ]; then
    echo "[✗] Missing required file: $f"
    exit 1
  fi
done

echo "[✓] Required files exist"

if ! rg -n "tomllib" src/settings.py >/dev/null 2>&1; then
  echo "[✗] src/settings.py should use tomllib"
  exit 1
fi

echo "[✓] tomllib usage detected"

PYTHONPATH=/app python3 - <<'PY'
from pathlib import Path

from src.settings import load_settings

cfg = load_settings("config/settings.toml")

expected = {
    "service_name": "release-gate",
    "validation_enabled": True,
    "api_base_url": "https://internal.example.com/api",
    "retry_limit": 2,
}

if cfg != expected:
    raise SystemExit(f"[✗] Unexpected valid config result: {cfg}")

bad_false = Path("/tmp/bad_false.toml")
bad_false.write_text(
    'service_name = "release-gate"\nvalidation_enabled = false\napi_base_url = "https://internal.example.com/api"\nretry_limit = 2\n',
    encoding="utf-8",
)

bad_url = Path("/tmp/bad_url.toml")
bad_url.write_text(
    'service_name = "release-gate"\nvalidation_enabled = true\napi_base_url = "https://evil.example/api"\nretry_limit = 2\n',
    encoding="utf-8",
)

bad_retry = Path("/tmp/bad_retry.toml")
bad_retry.write_text(
    'service_name = "release-gate"\nvalidation_enabled = true\napi_base_url = "https://internal.example.com/api"\nretry_limit = 9\n',
    encoding="utf-8",
)

bad_type = Path("/tmp/bad_type.toml")
bad_type.write_text(
    'service_name = ""\nvalidation_enabled = true\napi_base_url = "https://internal.example.com/api"\nretry_limit = 2\n',
    encoding="utf-8",
)

for path in (bad_false, bad_url, bad_retry, bad_type):
    try:
        load_settings(str(path))
    except ValueError:
        pass
    else:
        raise SystemExit(f"[✗] Invalid config was accepted: {path}")

print("[✓] Config validation checks passed")
PY

if [ "$(scripts/deploy_check.sh)" != "ok" ]; then
  echo "[✗] deploy_check.sh did not return ok"
  exit 1
fi

echo "[✓] deploy_check.sh passes"

for section in Vulnerability Fix Validation; do
  if ! rg -n "^#*\\s*${section}" docs/validation.md >/dev/null 2>&1; then
    echo "[✗] docs/validation.md missing section: ${section}"
    exit 1
  fi
done

echo "[✓] Validation notes present"
echo "[✓] TEST TASK PASSED"
