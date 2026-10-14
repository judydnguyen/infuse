#!/usr/bin/env bash
set -euo pipefail

echo "[verify] Checking installed packages..."

REQUIRED=("numpy" "requests")
MISSING=()

for pkg in "${REQUIRED[@]}"; do
    if ! pip show "$pkg" &>/dev/null; then
        MISSING+=("$pkg")
    fi
done

if [ ${#MISSING[@]} -ne 0 ]; then
    echo "[verify] FAILED — missing packages: ${MISSING[*]}"
    exit 1
fi

echo "[verify] PASS"
exit 0