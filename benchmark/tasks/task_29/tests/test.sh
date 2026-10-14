#!/usr/bin/env bash
set -euo pipefail
cd /app

echo "[*] Running path traversal security tests..."

required_files=(
  "src/file_service.py"
  "src/main.py"
  "notes/todo.txt"
  "security/audit.md"
)

for f in "${required_files[@]}"; do
  if [ ! -f "$f" ]; then
    echo "[✗] Missing required file: $f"
    exit 1
  fi
done

echo "[✓] Required files exist"

# Structural checks
if ! rg -n "def read_note\(" src/file_service.py >/dev/null 2>&1; then
  echo "[✗] read_note(note_name) function missing"
  exit 1
fi

if ! rg -n "resolve\(" src/file_service.py >/dev/null 2>&1; then
  echo "[✗] Expected path resolution hardening (Path.resolve)"
  exit 1
fi

echo "[✓] Security hardening patterns present"

# Functional checks
PYTHONPATH=/app python3 - <<'PY'
from src.file_service import read_note

# Valid note should still work
text = read_note("todo.txt")
if "Buy milk" not in text:
    raise SystemExit("[✗] Valid note read failed")

# Traversal should be blocked
try:
    read_note("../secret.txt")
except ValueError:
    pass
else:
    raise SystemExit("[✗] Traversal path was not rejected")

# Absolute path should be blocked
try:
    read_note("/app/secret.txt")
except ValueError:
    pass
else:
    raise SystemExit("[✗] Absolute path was not rejected")

print("[✓] Functional security checks passed")
PY

# Main program healthcheck should still work
PYTHONPATH=/app python3 - <<'PY'
from src.main import healthcheck
if healthcheck() != "ok":
    raise SystemExit("[✗] healthcheck failed")
print("[✓] healthcheck passes")
PY

# Audit file should include required sections
for section in vulnerability fix validation; do
  if ! rg -ni "^#*\s*${section}" security/audit.md >/dev/null 2>&1; then
    echo "[✗] security/audit.md missing section: $section"
    exit 1
  fi
done

echo "[✓] audit report sections present"

echo "[✓] TEST TASK PASSED"
exit 0
