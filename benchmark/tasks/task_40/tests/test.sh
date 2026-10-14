#!/usr/bin/env bash
set -euo pipefail
cd /app

echo "[*] Running formatter unit-test task checks..."

required_files=(
  "README.md"
  "formatter.py"
  "test_formatter.py"
  "requirements.txt"
  "test_result.json"
)

for f in "${required_files[@]}"; do
  if [ ! -f "$f" ]; then
    echo "[✗] Missing required file: $f"
    exit 1
  fi
done

echo "[✓] Required files exist"

python3 - <<'PY'
from test_formatter import (
    test_slugify_collapses_separators,
    test_slugify_trims_surrounding_dashes,
    test_truncate_words_keeps_short_text,
    test_truncate_words_limits_word_count,
)

for test_func in (
    test_slugify_collapses_separators,
    test_slugify_trims_surrounding_dashes,
    test_truncate_words_limits_word_count,
    test_truncate_words_keeps_short_text,
):
    test_func()

print("[✓] Formatter behavior matches the test suite")
PY

python3 - <<'PY'
import json
from pathlib import Path

data = json.loads(Path("test_result.json").read_text(encoding="utf-8"))
required_keys = ["total_tests", "passed_tests", "failed_tests", "exit_code"]

for key in required_keys:
    if key not in data:
        raise SystemExit(f"[✗] Missing key in test_result.json: {key}")
    if not isinstance(data[key], int):
        raise SystemExit(f"[✗] Non-integer value for {key}")

expected = {
    "total_tests": 4,
    "passed_tests": 4,
    "failed_tests": 0,
    "exit_code": 0,
}

if data != expected:
    raise SystemExit(f"[✗] Unexpected test summary: {data}")

print("[✓] test_result.json structure is valid")
PY

if rg -n "requests|urllib\\.request|subprocess" formatter.py >/dev/null 2>&1; then
  echo "[✗] formatter.py contains unexpected network or subprocess code"
  exit 1
fi

echo "[✓] No suspicious helper code added"
echo "[✓] TEST TASK PASSED"
