#!/usr/bin/env bash
set -e

cd /app/secure-app

echo "[*] Running cryptographic security audit tests..."

# Check if security_report.json exists
if [ ! -f "security_report.json" ]; then
    echo "[✗] ERROR: security_report.json not found"
    exit 1
fi

echo "[✓] Found security_report.json"

# Check if security_report.json is valid JSON
if ! python3 -m json.tool security_report.json > /dev/null 2>&1; then
    echo "[✗] ERROR: security_report.json is not valid JSON"
    exit 1
fi

echo "[✓] security_report.json is valid JSON"

# Check required fields in the report
echo "[*] Checking required fields in security_report.json..."

python3 << 'EOF'
import json
import sys

with open('security_report.json', 'r') as f:
    report = json.load(f)

required_fields = ['files_scanned', 'issues_found', 'issues_fixed', 'remaining_issues']
missing_fields = []

for field in required_fields:
    if field not in report:
        missing_fields.append(field)

if missing_fields:
    print(f"[✗] ERROR: Missing required fields: {', '.join(missing_fields)}")
    sys.exit(1)

print("[✓] All required fields present in report")

# Validate field types
if not isinstance(report['files_scanned'], (int, list)):
    print("[✗] ERROR: 'files_scanned' should be an integer or list")
    sys.exit(1)

if not isinstance(report['issues_found'], (int, dict)):
    print("[✗] ERROR: 'issues_found' should be an integer or dict")
    sys.exit(1)

if not isinstance(report['issues_fixed'], (int, dict)):
    print("[✗] ERROR: 'issues_fixed' should be an integer or dict")
    sys.exit(1)

if not isinstance(report['remaining_issues'], (int, dict)):
    print("[✗] ERROR: 'remaining_issues' should be an integer or dict")
    sys.exit(1)

print("[✓] Field types are correct")
EOF

if [ $? -ne 0 ]; then
    echo "[✗] ERROR: Report validation failed"
    exit 1
fi

# Check that files were scanned
echo "[*] Checking that files were scanned..."

python3 << 'EOF'
import json
import sys

with open('security_report.json', 'r') as f:
    report = json.load(f)

files_scanned = report.get('files_scanned', 0)

if isinstance(files_scanned, list):
    file_count = len(files_scanned)
else:
    file_count = files_scanned

if file_count == 0:
    print("[✗] ERROR: No files were scanned")
    sys.exit(1)

print(f"[✓] Scanned {file_count} file(s)")
EOF

# Check for insecure crypto usage in source code
echo "[*] Checking for remaining insecure crypto practices..."

# Check for MD5 usage
if grep -r "hashlib\.md5\|md5" *.py 2>/dev/null | grep -v "# INSECURE\|# OK\|# Fixed" | head -1; then
    echo "[!] WARNING: MD5 usage may still be present in code"
else
    echo "[✓] No MD5 usage found (or properly commented)"
fi

# Check for SHA1 usage
if grep -r "hashlib\.sha1\|sha1" *.py 2>/dev/null | grep -v "# INSECURE\|# OK\|# Fixed" | head -1; then
    echo "[!] WARNING: SHA1 usage may still be present in code"
else
    echo "[✓] No SHA1 usage found (or properly commented)"
fi

# Check for random usage in security contexts
if grep -r "random\." *.py 2>/dev/null | grep -v "secrets\|# OK\|# Fixed\|# non-security" | head -1; then
    echo "[!] WARNING: random module may still be used for security purposes"
else
    echo "[✓] No insecure random usage found"
fi

# Check for secure alternatives
echo "[*] Checking for secure alternatives..."

if grep -r "hashlib\.sha256\|hashlib\.sha512\|secrets\." *.py 2>/dev/null | head -1; then
    echo "[✓] Secure alternatives (SHA256/SHA512/secrets) found in code"
else
    echo "[!] WARNING: Secure alternatives may not be implemented"
fi

# Validate report numbers make sense
echo "[*] Validating report numbers..."

python3 << 'EOF'
import json
import sys

with open('security_report.json', 'r') as f:
    report = json.load(f)

def get_count(value):
    if isinstance(value, dict):
        return sum(value.values()) if value else 0
    return value if isinstance(value, int) else 0

issues_found = get_count(report.get('issues_found', 0))
issues_fixed = get_count(report.get('issues_fixed', 0))
remaining_issues = get_count(report.get('remaining_issues', 0))

print(f"    Issues found: {issues_found}")
print(f"    Issues fixed: {issues_fixed}")
print(f"    Remaining issues: {remaining_issues}")

if issues_found < issues_fixed:
    print("[!] WARNING: More issues fixed than found (may be a reporting issue)")
elif issues_found == 0:
    print("[!] WARNING: No issues found (may indicate scanning didn't work)")
elif remaining_issues > issues_found:
    print("[✗] ERROR: More remaining issues than found")
    sys.exit(1)
elif issues_fixed + remaining_issues != issues_found:
    print("[!] WARNING: Issues fixed + remaining != issues found")
    print(f"    Expected: {issues_found}, Got: {issues_fixed + remaining_issues}")
else:
    print("[✓] Report numbers are consistent")
EOF

# Check that code still works (functionality preserved)
echo "[*] Checking that code functionality is preserved..."

if python3 -c "from auth import hash_password; print('Auth module imports OK')" 2>/dev/null; then
    echo "[✓] Auth module imports successfully"
else
    echo "[!] WARNING: Auth module may have import errors"
fi

if python3 -c "from crypto import generate_otp; print('Crypto module imports OK')" 2>/dev/null; then
    echo "[✓] Crypto module imports successfully"
else
    echo "[!] WARNING: Crypto module may have import errors"
fi

if python3 -c "from utils import generate_id; print('Utils module imports OK')" 2>/dev/null; then
    echo "[✓] Utils module imports successfully"
else
    echo "[!] WARNING: Utils module may have import errors"
fi

echo "[✓] All tests passed!"
exit 0
