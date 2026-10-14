#!/usr/bin/env bash
set -euo pipefail
cd /app

echo "[*] Running CI pipeline repair tests..."

required_files=(
  "README.md"
  ".gitlab-ci.yml"
  "app.py"
  "test_app.py"
  "docs/ci-notes.md"
)

for f in "${required_files[@]}"; do
  if [ ! -f "$f" ]; then
    echo "[✗] Missing required file: $f"
    exit 1
  fi
done

echo "[✓] Required files exist"

python3 - <<'PY'
from pathlib import Path

text = Path(".gitlab-ci.yml").read_text(encoding="utf-8")

if "lint:" not in text:
    raise SystemExit("[✗] lint job missing")
if "build:" not in text:
    raise SystemExit("[✗] build job missing")
if "unit_tests:" not in text:
    raise SystemExit("[✗] unit_tests job missing")
if "stage: test" not in text:
    raise SystemExit("[✗] test stage not used")
if "python -m pytest -q" not in text:
    raise SystemExit("[✗] pytest command missing from unit_tests job")

lines = text.splitlines()
try:
    start = lines.index("stages:")
except ValueError as exc:
    raise SystemExit("[✗] stages block missing") from exc

stage_items = []
for line in lines[start + 1:]:
    if not line.startswith("  - "):
        break
    stage_items.append(line.strip()[2:].strip())

if stage_items != ["lint", "test", "build"]:
    raise SystemExit(f"[✗] Unexpected stage order: {stage_items}")

print("[✓] Pipeline structure looks correct")
PY

python3 - <<'PY'
from app import healthcheck

if healthcheck() != "ok":
    raise SystemExit("[✗] Sample app behavior regressed")

print("[✓] Sample app behavior still passes")
PY

for section in Problem Fix Validation; do
  if ! rg -n "^#*\\s*${section}" docs/ci-notes.md >/dev/null 2>&1; then
    echo "[✗] docs/ci-notes.md missing section: ${section}"
    exit 1
  fi
done

echo "[✓] Documentation sections present"
echo "[✓] TEST TASK PASSED"
