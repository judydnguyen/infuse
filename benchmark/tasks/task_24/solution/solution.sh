#!/usr/bin/env bash
set -euo pipefail
cd /app

echo "[*] Applying fix to process_zip.py..."

cat > process_zip.py << 'PYEOF'
"""
process_zip.py
Reads input.zip, extracts CSV files, and prints a sales summary.
FIXED: skips malformed CSV files gracefully instead of crashing.
"""
import csv
import zipfile
from pathlib import Path

ZIP_PATH = Path(__file__).parent / "input.zip"


def summarize_csv(content: str, filename: str) -> dict:
    """Parse CSV content and return summary stats."""
    reader = csv.DictReader(content.splitlines())

    total_sales = 0
    total_expenses = 0
    row_count = 0

    for row in reader:
        # FIXED: raise KeyError explicitly if columns missing
        # so the caller can catch and skip this file
        if "sales" not in row or "expenses" not in row:
            raise KeyError(f"Missing required columns in {filename}")
        total_sales += float(row["sales"])
        total_expenses += float(row["expenses"])
        row_count += 1

    return {
        "file": filename,
        "rows": row_count,
        "total_sales": total_sales,
        "total_expenses": total_expenses,
        "net_profit": total_sales - total_expenses,
    }


def process_zip(zip_path: Path) -> list:
    """Extract and summarize all CSV files from the zip."""
    results = []

    with zipfile.ZipFile(zip_path) as zf:
        for name in zf.namelist():
            if name.endswith(".csv"):
                content = zf.read(name).decode("utf-8")
                # FIXED: catch errors and skip malformed files gracefully
                try:
                    summary = summarize_csv(content, name)
                    results.append(summary)
                except (KeyError, ValueError) as e:
                    print(f"Skipping {name}: missing required columns")

    return results


if __name__ == "__main__":
    summaries = process_zip(ZIP_PATH)
    for s in summaries:
        print(f"\nFile: {s['file']}")
        print(f"  Rows:          {s['rows']}")
        print(f"  Total Sales:   ${s['total_sales']:,.2f}")
        print(f"  Total Expenses:${s['total_expenses']:,.2f}")
        print(f"  Net Profit:    ${s['net_profit']:,.2f}")
PYEOF

echo "[✓] Fix applied. Running verification..."
bash /tests/test.sh
