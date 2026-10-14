#!/usr/bin/env bash
set -euo pipefail
cd /app

echo "[*] Applying fix to logger.py..."

cat > logger.py << 'PYEOF'
"""Logger module."""
import os
import shutil
from datetime import datetime


LEVEL_MAP = {
    "DEBUG": 10,
    "INFO": 20,
    "WARNING": 30,
    "ERROR": 40,
    "CRITICAL": 50,
}


def parse_log_level(level):
    # FIXED: handle invalid log level
    upper = level.upper()
    if upper not in LEVEL_MAP:
        raise ValueError(f"Invalid log level: {level}")
    return LEVEL_MAP[upper]


def rotate_log(path):
    # FIXED: handle missing log file
    if not os.path.exists(path):
        raise ValueError(f"Log file not found: {path}")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    archive_path = f"{path}.{timestamp}"
    shutil.move(path, archive_path)
    return archive_path


def write_log(path, level, message):
    level_num = parse_log_level(level)
    timestamp = datetime.now().isoformat()
    with open(path, "a") as f:
        f.write(f"[{timestamp}] [{level.upper()}] {message}\n")


def read_log(path):
    if not os.path.exists(path):
        return []
    with open(path, "r") as f:
        return f.readlines()


if __name__ == "__main__":
    write_log("app.log", "INFO", "Application started")
    print(read_log("app.log"))
PYEOF

echo "[✓] Fix applied. Running verification..."
bash /tests/test.sh
