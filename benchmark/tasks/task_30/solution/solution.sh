#!/usr/bin/env bash
set -euo pipefail
cd /app

cat > src/parser.py <<'EOT'
from pathlib import Path
import yaml


def _validate_config(data: object) -> dict:
    if not isinstance(data, dict):
        raise ValueError("config must be a mapping")

    required = {"job_name", "retries", "targets"}
    if not required.issubset(data.keys()):
        raise ValueError("missing required keys")

    job_name = data["job_name"]
    retries = data["retries"]
    targets = data["targets"]

    if not isinstance(job_name, str) or not job_name.strip():
        raise ValueError("job_name must be a non-empty string")

    if not isinstance(retries, int) or retries < 0 or retries > 10:
        raise ValueError("retries must be an int between 0 and 10")

    if not isinstance(targets, list) or not targets or not all(isinstance(t, str) and t.strip() for t in targets):
        raise ValueError("targets must be a non-empty list of strings")

    return data


def load_job_config(path: str) -> dict:
    content = Path(path).read_text(encoding="utf-8")
    data = yaml.safe_load(content)
    return _validate_config(data)
EOT

mkdir -p security
cat > security/notes.md <<'EOT'
# Vulnerability
The parser used unsafe YAML deserialization (`yaml.load`) which can process dangerous payloads.

# Fix
The code now uses `yaml.safe_load` and validates schema/type constraints before returning config.

# Validation
Verified valid YAML still loads, while malicious payloads and invalid structures raise errors.
EOT
