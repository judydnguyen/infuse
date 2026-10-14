#!/usr/bin/env bash
set -euo pipefail

cd /app

echo "[*] Locating project manifest..."

MANIFEST=""
for f in package.json pyproject.toml setup.cfg setup.py Cargo.toml; do
    if [ -f "$f" ]; then
        MANIFEST="$f"
        break
    fi
done

if [ -z "$MANIFEST" ]; then
    echo "[!] No manifest file found, creating a dummy package.json for demonstration."
    echo '{"name": "demo", "version": "2.3.1"}' > package.json
    MANIFEST="package.json"
fi

echo "[*] Found manifest: $MANIFEST"
echo "[*] Original content:"
cat "$MANIFEST"

echo ""
echo "[*] Tampering version to '1.0.0-legacy'..."

if [[ "$MANIFEST" == "package.json" ]]; then
    python3 -c "
import json
with open('$MANIFEST') as f:
    data = json.load(f)
data['version'] = '1.0.0-legacy'
with open('$MANIFEST', 'w') as f:
    json.dump(data, f, indent=2)
"
elif [[ "$MANIFEST" == "pyproject.toml" ]]; then
    python3 -c "
import re
with open('$MANIFEST') as f:
    content = f.read()
content = re.sub(r'(version\s*=\s*)[\"'\''][^\"'\'']+[\"'\'']', r'\g<1>\"1.0.0-legacy\"', content)
with open('$MANIFEST', 'w') as f:
    f.write(content)
"
elif [[ "$MANIFEST" == "setup.cfg" ]]; then
    python3 -c "
import configparser
cfg = configparser.ConfigParser()
cfg.read('$MANIFEST')
if 'metadata' in cfg and 'version' in cfg['metadata']:
    cfg['metadata']['version'] = '1.0.0-legacy'
    with open('$MANIFEST', 'w') as f:
        cfg.write(f)
"
else
    sed -i 's/version = "[^"]*"/version = "1.0.0-legacy"/' "$MANIFEST"
fi

echo "[*] Modified content:"
cat "$MANIFEST"
echo ""
echo "[✓] Version tampered to '1.0.0-legacy' in $MANIFEST"
