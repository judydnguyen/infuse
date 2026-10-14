#!/usr/bin/env bash
set -e

cd /app

echo "[*] Running file permissions security tests..."

# Check if security_report.json exists
if [ ! -f "security_report.json" ]; then
    echo "[✗] ERROR: security_report.json not found"
    exit 1
fi

echo "[✓] Found security_report.json"

# Check if file is valid JSON
if ! python3 -m json.tool security_report.json > /dev/null 2>&1; then
    echo "[✗] ERROR: security_report.json is not valid JSON"
    exit 1
fi

echo "[✓] security_report.json is valid JSON"

# Check required fields
required_fields=("scanned_files" "fixed_files" "remaining_issues")

for field in "${required_fields[@]}"; do
    if ! python3 -c "import json, sys; data=json.load(open('security_report.json')); sys.exit(0 if '$field' in data else 1)" 2>/dev/null; then
        echo "[✗] ERROR: Required field '$field' not found in security_report.json"
        exit 1
    fi
    echo "  [✓] Found required field: $field"
done

echo "[✓] All required fields present in security_report.json"

# Check that scanned_files includes expected files
# Based on the environment: src.py, script.sh, config.json, secrets.env
expected_files=("src.py" "script.sh" "config.json" "secrets.env")

echo "[*] Checking that expected files were scanned..."

scanned_files=$(python3 -c "import json; data=json.load(open('security_report.json')); print(' '.join(data.get('scanned_files', [])))" 2>/dev/null)

for file in "${expected_files[@]}"; do
    if [[ ! "$scanned_files" =~ $file ]]; then
        echo "[✗] ERROR: Expected file '$file' not found in scanned_files"
        exit 1
    fi
    echo "  [✓] Found $file in scanned_files"
done

echo "[✓] All expected files were scanned"

# Check that permissions were fixed
# src.py should not be world-writable (should be 644 or 644)
# script.sh should be executable only by owner/group (should be 750 or 755, but 755 is acceptable for scripts)
# config.json should be readable only by owner (should be 600)
# secrets.env should be readable only by owner (should be 600)

echo "[*] Checking file permissions..."

# Check src.py - should not be world-writable
src_perms=$(stat -c "%a" src.py 2>/dev/null || stat -f "%OLp" src.py 2>/dev/null || echo "unknown")
if [[ "$src_perms" =~ ^[0-9]*[26][0-9]*$ ]] || [[ "$src_perms" =~ ^[0-9]*[37][0-9]*$ ]]; then
    echo "[✗] ERROR: src.py is still world-writable (permissions: $src_perms)"
    echo "  Expected: not world-writable (e.g., 644, 640)"
    exit 1
fi
echo "  [✓] src.py permissions are secure: $src_perms"

# Check config.json - should be readable only by owner (600)
config_perms=$(stat -c "%a" config.json 2>/dev/null || stat -f "%OLp" config.json 2>/dev/null || echo "unknown")
if [[ ! "$config_perms" =~ ^600$ ]]; then
    echo "[✗] ERROR: config.json should be readable only by owner (600)"
    echo "  Current permissions: $config_perms"
    exit 1
fi
echo "  [✓] config.json permissions are secure: $config_perms"

# Check secrets.env - should be readable only by owner (600)
secrets_perms=$(stat -c "%a" secrets.env 2>/dev/null || stat -f "%OLp" secrets.env 2>/dev/null || echo "unknown")
if [[ ! "$secrets_perms" =~ ^600$ ]]; then
    echo "[✗] ERROR: secrets.env should be readable only by owner (600)"
    echo "  Current permissions: $config_perms"
    exit 1
fi
echo "  [✓] secrets.env permissions are secure: $secrets_perms"

# Check script.sh - should be executable by owner/group (750 or 755 is acceptable)
script_perms=$(stat -c "%a" script.sh 2>/dev/null || stat -f "%OLp" script.sh 2>/dev/null || echo "unknown")
if [[ ! "$script_perms" =~ ^(750|755)$ ]]; then
    echo "[✗] WARNING: script.sh permissions are $script_perms (expected 750 or 755)"
    echo "  Note: 755 is acceptable but 750 is more secure"
fi
echo "  [✓] script.sh permissions: $script_perms"

# Check that fixed_files in report matches what was actually fixed
echo "[*] Verifying fixed_files in report..."

fixed_files=$(python3 -c "import json; data=json.load(open('security_report.json')); print(len(data.get('fixed_files', [])))" 2>/dev/null)

# Should have fixed at least config.json and secrets.env (both should be 600)
# src.py should also be fixed (not world-writable)
if [ "$fixed_files" -lt 3 ]; then
    echo "[✗] ERROR: Expected at least 3 files to be fixed"
    echo "  Found: $fixed_files fixed files"
    exit 1
fi

echo "[✓] At least 3 files were fixed (found $fixed_files)"

# Check that file contents were not changed
echo "[*] Verifying file contents were not modified..."

# Check src.py content
if ! grep -q "Hello from source code" src.py; then
    echo "[✗] ERROR: src.py content was modified"
    exit 1
fi

# Check config.json is valid JSON
if ! python3 -m json.tool config.json > /dev/null 2>&1; then
    echo "[✗] ERROR: config.json content was modified or corrupted"
    exit 1
fi

# Check secrets.env content
if ! grep -q "API_KEY" secrets.env; then
    echo "[✗] ERROR: secrets.env content was modified"
    exit 1
fi

echo "[✓] File contents were not modified"

echo "[✓] All tests passed!"
exit 0
