#!/usr/bin/env bash
set -euo pipefail
cd /app

echo "[*] Applying fix to calculator.py..."

cat > calculator.py << 'PYEOF'
"""Simple calculator module."""


def add(a, b):
    return a + b


def subtract(a, b):
    return a - b


def multiply(a, b):
    return a * b


def divide(a, b):
    # FIXED: raise ValueError on division by zero
    if b == 0:
        raise ValueError("Cannot divide by zero")
    return a / b


def power(a, b):
    return a ** b


def average(numbers):
    # FIXED: raise ValueError on empty list
    if not numbers:
        raise ValueError("Cannot average an empty list")
    return sum(numbers) / len(numbers)


if __name__ == "__main__":
    print(add(2, 3))
    print(divide(10, 2))
    print(average([1, 2, 3]))
PYEOF

echo "[✓] Fix applied. Running verification..."
bash /tests/test.sh
