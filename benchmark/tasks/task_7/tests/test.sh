#!/usr/bin/env bash
set -e

cd /app

echo "[*] Running dependency lock file tests..."

# Check if requirements.lock file exists
if [ ! -f "requirements.lock" ]; then
    echo "[✗] ERROR: requirements.lock not found"
    exit 1
fi

echo "[✓] Found requirements.lock"

# Check if file is not empty
if [ ! -s "requirements.lock" ]; then
    echo "[✗] ERROR: requirements.lock is empty"
    exit 1
fi

echo "[✓] requirements.lock is not empty"

# Check that all necessary dependencies are present
# Based on the environment files:
# - main.py uses: requests, numpy, flask
# - utils.py uses: pandas, matplotlib
# - requirements.txt specifies: requests, numpy, flask, pandas, matplotlib
required_packages=("flask" "matplotlib" "numpy" "pandas" "requests")

echo "[*] Checking that all required dependencies are in requirements.lock..."

for package in "${required_packages[@]}"; do
    # Check if package is in requirements.lock (case-insensitive)
    if ! grep -qi "^${package}==" requirements.lock; then
        echo "[✗] ERROR: Required package '$package' not found in requirements.lock"
        exit 1
    fi
    
    echo "  [✓] Found $package in requirements.lock"
done

echo "[✓] All required dependencies are present in requirements.lock"

# Check that all entries in requirements.lock use exact version pinning (==)
echo "[*] Checking that all entries use exact version pinning (==)..."
while IFS= read -r line || [ -n "$line" ]; do
    # Skip empty lines and comments
    [[ -z "$line" || "$line" =~ ^[[:space:]]*# ]] && continue
    
    # Check if line uses == for version pinning
    if [[ ! "$line" =~ ^[^=]+==[0-9] ]]; then
        echo "[✗] ERROR: Entry does not use exact version pinning (==): $line"
        echo "  All entries must use format: package==version"
        exit 1
    fi
done < requirements.lock

echo "[✓] All entries use exact version pinning (==)"

# Check that file is sorted alphabetically
echo "[*] Checking that requirements.lock is sorted alphabetically..."
sorted_file=$(mktemp)
# Filter out comments and empty lines, then sort
grep -v '^[[:space:]]*#' requirements.lock | grep -v '^[[:space:]]*$' | sort > "$sorted_file"

# Compare original (without comments/empty lines) with sorted
original_filtered=$(mktemp)
grep -v '^[[:space:]]*#' requirements.lock | grep -v '^[[:space:]]*$' > "$original_filtered"

if ! cmp -s "$original_filtered" "$sorted_file"; then
    echo "[✗] ERROR: requirements.lock is not sorted alphabetically"
    echo "  Expected sorted order:"
    head -5 "$sorted_file" | sed 's/^/    /'
    exit 1
fi

rm -f "$sorted_file" "$original_filtered"
echo "[✓] requirements.lock is sorted alphabetically"

# Check that all required packages are present (including transitive dependencies)
# The required packages are: flask, matplotlib, numpy, pandas, requests
# (from main.py: requests, numpy, flask; from utils.py: pandas, matplotlib)
req_lock_count=$(grep -v '^[[:space:]]*#' requirements.lock | grep -v '^[[:space:]]*$' | wc -l)

# Should have at least the 5 required packages (may have more due to transitive dependencies)
if [ "$req_lock_count" -lt 5 ]; then
    echo "[✗] ERROR: requirements.lock has too few dependencies"
    echo "  Expected at least 5 (flask, matplotlib, numpy, pandas, requests + transitive deps)"
    echo "  Found: $req_lock_count"
    exit 1
fi

echo "[✓] Dependency count check passed (found $req_lock_count dependencies, expected at least 5)"

echo "[✓] All tests passed!"
exit 0
