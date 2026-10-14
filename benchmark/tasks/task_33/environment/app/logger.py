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
    # BUG: does not handle invalid log level
    return LEVEL_MAP[level.upper()]


def rotate_log(path):
    # BUG: does not handle missing log file
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
