#!/usr/bin/env bash
set -euo pipefail
cd /app

echo "[*] Applying fix to config_loader.py..."

cat > config_loader.py << 'PYEOF'
"""Config loader module."""
import yaml
import os


def load_config(path):
    # FIXED: handle missing file
    if not os.path.exists(path):
        raise ValueError(f"Config file not found: {path}")
    with open(path, "r") as f:
        return yaml.safe_load(f)


def get_config_value(config, key):
    # FIXED: handle missing key
    if key not in config:
        raise ValueError(f"Config key not found: {key}")
    return config[key]


def get_nested_value(config, *keys):
    result = config
    for key in keys:
        result = result[key]
    return result


def merge_configs(base, override):
    merged = base.copy()
    merged.update(override)
    return merged


if __name__ == "__main__":
    config = load_config("config.yaml")
    print(get_config_value(config, "app_name"))
PYEOF

echo "[✓] Fix applied. Running verification..."
bash /tests/test.sh
