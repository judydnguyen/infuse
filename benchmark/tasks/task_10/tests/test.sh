#!/usr/bin/env bash
set -e

cd /app

echo "[*] Running disk usage measurement tests..."

# Check if disk_usage.json exists
if [ ! -f "disk_usage.json" ]; then
    echo "[✗] ERROR: disk_usage.json not found"
    exit 1
fi

echo "[✓] Found disk_usage.json"

# Check if file is valid JSON
if ! python3 -m json.tool disk_usage.json > /dev/null 2>&1; then
    echo "[✗] ERROR: disk_usage.json is not valid JSON"
    exit 1
fi

echo "[✓] disk_usage.json is valid JSON"

# Check that it's a JSON array
is_array=$(python3 -c "import json; data=json.load(open('disk_usage.json')); print('yes' if isinstance(data, list) else 'no')" 2>/dev/null)
if [ "$is_array" != "yes" ]; then
    echo "[✗] ERROR: disk_usage.json should be a JSON array"
    exit 1
fi

echo "[✓] disk_usage.json is a JSON array"

# Check that it has at most 5 entries (top 5)
entry_count=$(python3 -c "import json; data=json.load(open('disk_usage.json')); print(len(data))" 2>/dev/null)
if [ "$entry_count" -gt 5 ]; then
    echo "[✗] ERROR: disk_usage.json should have at most 5 entries (top 5)"
    echo "  Found: $entry_count entries"
    exit 1
fi

echo "[✓] disk_usage.json has $entry_count entries (at most 5)"

# Check required fields in each entry
echo "[*] Checking required fields in each entry..."

python3 << 'EOF'
import json
import sys

with open('disk_usage.json') as f:
    data = json.load(f)

if len(data) == 0:
    print("[✗] ERROR: disk_usage.json is empty")
    sys.exit(1)

# Accept either 'path' or 'directory' as the directory field name
path_field = None
for i, entry in enumerate(data):
    # Determine which field name is used for directory path
    if path_field is None:
        if 'path' in entry:
            path_field = 'path'
        elif 'directory' in entry:
            path_field = 'directory'
        else:
            print(f"[✗] ERROR: Entry {i} missing 'path' or 'directory' field")
            sys.exit(1)

    if path_field not in entry:
        print(f"[✗] ERROR: Entry {i} missing '{path_field}' field")
        sys.exit(1)

    # Accept various field names for size: size_bytes, size, bytes
    size_field = None
    for sf in ['size_bytes', 'size', 'bytes']:
        if sf in entry:
            size_field = sf
            break

    if size_field is None:
        print(f"[✗] ERROR: Entry {i} missing size field (size_bytes, size, or bytes)")
        sys.exit(1)

    if not isinstance(entry[size_field], (int, float)):
        print(f"[✗] ERROR: Entry {i} '{size_field}' should be a number")
        sys.exit(1)

print(f"[✓] All entries have required fields ({path_field}, size)")
EOF

# Check that entries are sorted by size in descending order
echo "[*] Checking sort order (descending by size)..."

python3 << 'EOF'
import json
import sys

with open('disk_usage.json') as f:
    data = json.load(f)

# Detect which size field is used
size_field = None
for sf in ['size_bytes', 'size', 'bytes']:
    if data and sf in data[0]:
        size_field = sf
        break

if size_field is None:
    print("[✗] ERROR: No size field found")
    sys.exit(1)

sizes = [entry[size_field] for entry in data]
if sizes != sorted(sizes, reverse=True):
    print("[✗] ERROR: Entries should be sorted by size in descending order")
    print(f"  Found sizes: {sizes}")
    sys.exit(1)

print("[✓] Entries are correctly sorted in descending order")
EOF

# Check that dir_large is in the top results (it should be the largest)
echo "[*] Checking that largest directories are captured..."

python3 << 'EOF'
import json
import sys

with open('disk_usage.json') as f:
    data = json.load(f)

# Detect which path field is used
path_field = 'path' if (data and 'path' in data[0]) else 'directory'
paths = [entry.get(path_field, '') for entry in data]

# dir_large should be the largest and appear first
if len(data) > 0 and 'dir_large' not in paths[0]:
    print(f"[!] WARNING: Expected 'dir_large' to be the largest, but found '{paths[0]}'")
    # This is a warning, not a failure - the actual sizes may vary

# At least check that we have some expected directories
expected_dirs = ['dir_large', 'dir_medium', 'dir_nested', 'dir_extra', 'dir_small']
found_expected = sum(1 for p in paths if any(d in p for d in expected_dirs))

if found_expected < 3:
    print(f"[✗] ERROR: Expected to find at least 3 of the test directories in results")
    print(f"  Found paths: {paths}")
    sys.exit(1)

print(f"[✓] Found {found_expected} expected directories in results")
EOF

echo "[✓] All tests passed!"
exit 0
