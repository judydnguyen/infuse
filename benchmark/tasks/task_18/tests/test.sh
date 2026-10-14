#!/usr/bin/env bash
set -euo pipefail

cd /app/login-system

echo "[*] Running login system bug fix verification..."

# Run the npm tests
echo "[*] Running npm test..."
if npm test 2>&1; then
    echo "[✓] All tests passed"
else
    echo "[✗] Some tests failed"
    exit 1
fi

# Additional verification of the bug fixes
echo "[*] Verifying bug fixes in auth.js..."

# Check Bug 1: Password comparison logic should return success when passwords match
if grep -q "if (passwordMatch)" src/auth.js && grep -q "success: true" src/auth.js; then
    echo "[✓] Bug 1: Password comparison logic appears fixed"
else
    echo "[!] Bug 1: Password comparison logic may not be correctly fixed"
fi

# Check Bug 2: Should use EMAIL_HOST instead of EMAIL_SERVER
if grep -q "EMAIL_HOST" src/auth.js; then
    echo "[✓] Bug 2: Email configuration uses correct environment variable"
elif grep -q "EMAIL_SERVER" src/auth.js; then
    echo "[✗] Bug 2: Email configuration still uses wrong environment variable (EMAIL_SERVER)"
    exit 1
fi

# Check Bug 3: Token expiration check should return true when token is expired (now - timestamp >= oneHour)
if grep -q "return.*>.*oneHour" src/auth.js || grep -q "return.*>=.*oneHour" src/auth.js; then
    echo "[✓] Bug 3: Token expiration logic appears fixed"
else
    echo "[!] Bug 3: Token expiration logic may not be correctly fixed"
fi

echo "[✓] TEST TASK PASSED"
exit 0
