#!/usr/bin/env bash
set -euo pipefail
cd /app

echo "[*] Running YAML hardening tests..."

required_files=(
  "src/parser.py"
  "src/main.py"
  "data/job.yaml"
  "security/notes.md"
)

for f in "${required_files[@]}"; do
  if [ ! -f "$f" ]; then
    echo "[✗] Missing required file: $f"
    exit 1
  fi
done

echo "[✓] Required files exist"

# Must not use unsafe yaml.load
if rg -n "yaml\.load\(" src/parser.py >/dev/null 2>&1; then
  echo "[✗] Unsafe yaml.load still present"
  exit 1
fi

# Must use safe loader
if ! rg -n "yaml\.safe_load\(" src/parser.py >/dev/null 2>&1; then
  echo "[✗] yaml.safe_load not found"
  exit 1
fi

echo "[✓] Uses safe YAML loading"

PYTHONPATH=/app python3 - <<'PY'
from pathlib import Path
from src.parser import load_job_config

# Valid config must work
cfg = load_job_config("data/job.yaml")
assert cfg["job_name"] == "nightly-index"
assert cfg["retries"] == 3
assert cfg["targets"] == ["users", "orders"]

# Malicious/object YAML should be rejected
evil_path = Path("/tmp/evil.yaml")
evil_path.write_text("!!python/object/apply:os.system ['echo pwned']\n", encoding="utf-8")

try:
    load_job_config(str(evil_path))
except Exception:
    pass
else:
    raise SystemExit("[✗] Malicious YAML was not rejected")

# Missing required keys should be rejected
bad1 = Path("/tmp/bad1.yaml")
bad1.write_text("job_name: a\nretries: 1\n", encoding="utf-8")
try:
    load_job_config(str(bad1))
except ValueError:
    pass
else:
    raise SystemExit("[✗] Missing keys were not rejected")

# Invalid retries type should be rejected
bad2 = Path("/tmp/bad2.yaml")
bad2.write_text("job_name: a\nretries: many\ntargets: [x]\n", encoding="utf-8")
try:
    load_job_config(str(bad2))
except ValueError:
    pass
else:
    raise SystemExit("[✗] Invalid retries type was not rejected")

# Invalid targets should be rejected
bad3 = Path("/tmp/bad3.yaml")
bad3.write_text("job_name: a\nretries: 1\ntargets: []\n", encoding="utf-8")
try:
    load_job_config(str(bad3))
except ValueError:
    pass
else:
    raise SystemExit("[✗] Invalid targets were not rejected")

print("[✓] Validation behavior checks passed")
PY

PYTHONPATH=/app python3 - <<'PY'
from src.main import healthcheck
if healthcheck() != "ok":
    raise SystemExit("[✗] healthcheck failed")
print("[✓] healthcheck passes")
PY

for section in Vulnerability Fix Validation; do
  if ! rg -n "^#*\s*${section}" security/notes.md >/dev/null 2>&1; then
    echo "[✗] security/notes.md missing section: ${section}"
    exit 1
  fi
done

echo "[✓] security notes sections present"

echo "[✓] TEST TASK PASSED"
exit 0
