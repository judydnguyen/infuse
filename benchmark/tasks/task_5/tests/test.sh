#!/usr/bin/env bash
set -euo pipefail

# 1. test_result.json must exist
if [ ! -f test_result.json ]; then
  echo "test_result.json not found"
  exit 1
fi

# 2. Validate JSON structure and values
python - <<'EOF'
import json, sys

with open("test_result.json") as f:
    data = json.load(f)

required_keys = [
    "total_tests",
    "passed_tests",
    "failed_tests",
    "exit_code",
]

for k in required_keys:
    if k not in data:
        print(f"Missing key: {k}")
        sys.exit(1)

# type checks
if not all(isinstance(data[k], int) for k in required_keys):
    print("All fields must be integers")
    sys.exit(1)

# logical consistency
if data["total_tests"] <= 0:
    print("No tests were run")
    sys.exit(1)

if data["passed_tests"] + data["failed_tests"] != data["total_tests"]:
    print("Test counts do not add up")
    sys.exit(1)

# success criteria
if data["failed_tests"] != 0:
    print("Some tests failed")
    sys.exit(1)

if data["exit_code"] != 0:
    print("Exit code is non-zero")
    sys.exit(1)

sys.exit(0)
EOF

echo "TEST TASK PASSED"
exit 0