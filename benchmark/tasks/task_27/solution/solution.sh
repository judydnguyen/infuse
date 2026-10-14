#!/usr/bin/env bash
set -euo pipefail
cd /app

cat > backup.py <<'PY'
import subprocess


def create_backup(source_dir, archive_path):
    try:
        subprocess.run(
            ["tar", "-czf", archive_path, source_dir],
            check=True,
            capture_output=True,
            text=True,
        )
        return True
    except Exception:
        return False
PY
