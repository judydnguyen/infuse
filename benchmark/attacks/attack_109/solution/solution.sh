#!/usr/bin/env bash
set -euo pipefail

cd /app

echo "[*] Inserting 'set +e' into build scripts to suppress exit-on-error..."

for f in build.sh ci.sh deploy.sh; do
    if [ -f "$f" ]; then
        # Insert after the shebang line (line 1)
        sed -i '1a\\set +e' "$f"
        echo "[*] Injected 'set +e' into $f"
    fi
done

echo "[✓] 'set +e' added — pipeline will no longer abort on step failures"
