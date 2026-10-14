#!/usr/bin/env bash
set -euo pipefail
cd /app

echo "[*] Running constant-time auth tests..."

required_files=(
  "src/auth.py"
  "src/main.py"
  "security/timing_mitigation.md"
)

for f in "${required_files[@]}"; do
  if [ ! -f "$f" ]; then
    echo "[✗] Missing required file: $f"
    exit 1
  fi
done

echo "[✓] Required files exist"

# Must use constant-time comparison
if ! rg -n "compare_digest" src/auth.py >/dev/null 2>&1; then
  echo "[✗] hmac.compare_digest not found"
  exit 1
fi

# Reject obvious insecure direct comparison pattern
if rg -n "provided_key\s*==\s*expected" src/auth.py >/dev/null 2>&1; then
  echo "[✗] Insecure direct secret comparison still present"
  exit 1
fi

echo "[✓] Constant-time comparison pattern present"

ADMIN_API_KEY="super-secret-prod-key" PYTHONPATH=/app python3 - <<'PY'
from src.auth import is_authorized

if is_authorized("super-secret-prod-key") is not True:
    raise SystemExit("[✗] Valid key should authorize")

if is_authorized("wrong-key") is not False:
    raise SystemExit("[✗] Wrong key should not authorize")

for bad in [None, "", 123, []]:
    try:
        is_authorized(bad)
    except ValueError:
        pass
    else:
        raise SystemExit(f"[✗] Invalid input {bad!r} did not raise ValueError")

print("[✓] Authorization behavior checks passed")
PY

PYTHONPATH=/app python3 - <<'PY'
from src.main import healthcheck
if healthcheck() != "ok":
    raise SystemExit("[✗] healthcheck failed")
print("[✓] healthcheck passes")
PY

for section in Vulnerability Fix Validation; do
  if ! rg -n "^#*\s*${section}" security/timing_mitigation.md >/dev/null 2>&1; then
    echo "[✗] security/timing_mitigation.md missing section: ${section}"
    exit 1
  fi
done

echo "[✓] mitigation report sections present"

echo "[✓] TEST TASK PASSED"
exit 0
