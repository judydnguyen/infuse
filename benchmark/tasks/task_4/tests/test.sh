#!/usr/bin/env bash
set -euo pipefail

# Run evaluation
python eval.py

# Verify result file exists
test -f test_result.json

# Basic sanity check on JSON content
python - <<'EOF'
import json, sys

with open("test_result.json") as f:
    data = json.load(f)

required = ["dataset", "metric", "accuracy", "pass"]
for k in required:
    if k not in data:
        sys.exit(1)

if not isinstance(data["accuracy"], float):
    sys.exit(1)

sys.exit(0)
EOF