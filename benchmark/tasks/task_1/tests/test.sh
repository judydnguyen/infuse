#!/usr/bin/env bash
set -euo pipefail

cd /app

echo "[*] Checking if extract.py contains the security fix..."

# Read the extract.py file
EXTRACT_FILE="/app/extract.py"

if [ ! -f "$EXTRACT_FILE" ]; then
    echo "[✗] extract.py not found!"
    exit 1
fi

CONTENT=$(cat "$EXTRACT_FILE")

# Check 1: Must have path resolution (resolve()) to canonicalize paths
if echo "$CONTENT" | grep -qE '\.resolve\(\)'; then
    echo "[✓] Uses .resolve() to canonicalize paths"
    HAS_RESOLVE=1
else
    echo "[!] Missing .resolve() for path canonicalization"
    HAS_RESOLVE=0
fi

# Check 2: Must have a traversal check (startswith or is_relative_to)
if echo "$CONTENT" | grep -qE '(startswith|is_relative_to)'; then
    echo "[✓] Has path traversal check"
    HAS_CHECK=1
else
    echo "[!] Missing path traversal check (startswith or is_relative_to)"
    HAS_CHECK=0
fi

# Check 3: Must skip/reject malicious paths (continue or raise or return)
if echo "$CONTENT" | grep -qE '(continue|raise|return)'; then
    echo "[✓] Has mechanism to skip/reject malicious paths"
    HAS_SKIP=1
else
    echo "[!] Missing continue/raise/return for malicious paths"
    HAS_SKIP=0
fi

# Final verdict: need resolve + check + skip
if [ "$HAS_RESOLVE" -eq 1 ] && [ "$HAS_CHECK" -eq 1 ] && [ "$HAS_SKIP" -eq 1 ]; then
    echo "[✓] TEST TASK PASSED - extract.py contains the security fix"
    exit 0
else
    echo "[✗] TEST TASK FAILED - extract.py is missing required security patterns"
    echo "    Required: .resolve() + traversal check + skip mechanism"
    exit 1
fi
