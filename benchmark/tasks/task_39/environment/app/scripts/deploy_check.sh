#!/usr/bin/env bash
set -euo pipefail
cd /app
PYTHONPATH=/app python3 - <<'PY'
from src.main import healthcheck
print(healthcheck())
PY
