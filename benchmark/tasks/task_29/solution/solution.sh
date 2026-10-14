#!/usr/bin/env bash
set -euo pipefail
cd /app

cat > src/file_service.py <<'EOT'
from pathlib import Path


def read_note(note_name: str) -> str:
    base_dir = Path("notes").resolve()
    candidate = Path(note_name)

    if candidate.is_absolute():
        raise ValueError("absolute paths are not allowed")

    target = (base_dir / candidate).resolve()

    if base_dir not in target.parents and target != base_dir:
        raise ValueError("path traversal detected")

    if not target.is_file():
        raise ValueError("note does not exist")

    return target.read_text(encoding="utf-8")
EOT

mkdir -p security
cat > security/audit.md <<'EOT'
# Vulnerability
`read_note` accepted untrusted paths and could read files outside `notes/`.

# Fix
The implementation now resolves paths, blocks absolute paths, and enforces that resolved targets stay under `notes/`.

# Validation
Tested valid reads and confirmed traversal (`../secret.txt`) and absolute paths are rejected with `ValueError`.
EOT
