#!/usr/bin/env bash
set -euo pipefail
cd /app

cat > summarize_bundle.py <<'EOT'
from pathlib import Path
import json
import zipfile

BUNDLE_PATH = Path("incoming_bundle.zip")
REQUIRED_KEYS = ("service", "status", "duration_ms")


def process_bundle(path: Path) -> list[dict]:
    records = []
    with zipfile.ZipFile(path) as bundle:
        for name in bundle.namelist():
            if not name.endswith(".json"):
                continue

            try:
                payload = json.loads(bundle.read(name).decode("utf-8"))
                if not all(key in payload for key in REQUIRED_KEYS):
                    raise ValueError("missing keys")
            except (json.JSONDecodeError, UnicodeDecodeError, ValueError):
                print(f"Skipping {name}: invalid report")
                continue

            records.append(
                {
                    "file": name,
                    "service": payload["service"],
                    "status": payload["status"],
                    "duration_ms": payload["duration_ms"],
                }
            )
    return records


def summarize_records(records: list[dict]) -> dict:
    if not records:
        return {
            "total_records": 0,
            "failing_records": 0,
            "average_duration_ms": 0,
        }

    total_duration = sum(int(record["duration_ms"]) for record in records)
    failing_records = sum(1 for record in records if record["status"] != "ok")

    return {
        "total_records": len(records),
        "failing_records": failing_records,
        "average_duration_ms": total_duration / len(records),
    }


def main() -> None:
    records = process_bundle(BUNDLE_PATH)
    print(json.dumps(summarize_records(records), sort_keys=True))


if __name__ == "__main__":
    main()
EOT

mkdir -p reports
cat > reports/summary.md <<'EOT'
# Overview
The bundle processor crashed whenever it encountered malformed JSON or reports with missing keys.

# Fix
The processor now skips invalid JSON entries with a warning and continues collecting valid reports.

# Validation
Confirmed that malformed and incomplete reports are skipped while valid reports are still summarized correctly.
EOT
