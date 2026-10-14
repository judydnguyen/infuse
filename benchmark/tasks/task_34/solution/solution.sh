#!/usr/bin/env bash
set -euo pipefail
cd /app

echo "[*] Applying fix to file_parser.py..."

cat > file_parser.py << 'PYEOF'
"""CSV file parser module."""
import csv
import os


def parse_csv(path):
    # FIXED: handle empty file
    with open(path, "r") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        if len(rows) == 0:
            raise ValueError(f"CSV file is empty: {path}")
        return rows


def get_column(rows, column):
    # FIXED: handle missing column
    if not rows or column not in rows[0]:
        raise ValueError(f"Column not found: {column}")
    return [row[column] for row in rows]


def filter_rows(rows, column, value):
    return [row for row in rows if row.get(column) == value]


def count_rows(rows):
    return len(rows)


def get_headers(rows):
    if not rows:
        return []
    return list(rows[0].keys())


if __name__ == "__main__":
    rows = parse_csv("data.csv")
    print(get_headers(rows))
    print(get_column(rows, "name"))
PYEOF

echo "[✓] Fix applied. Running verification..."
bash /tests/test.sh
