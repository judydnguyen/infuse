#!/usr/bin/env bash
set -euo pipefail

cd /app

echo "[*] Locating application config file..."

CONFIG=""
for f in config.yaml config.yml settings.yaml settings.yml app.yaml app.yml config.toml settings.toml .env; do
    if [ -f "$f" ]; then
        CONFIG="$f"
        break
    fi
done

if [ -z "$CONFIG" ]; then
    echo "[!] No config file found, creating a dummy config.yaml for demonstration."
    cat > config.yaml << 'EOF'
server:
  port: 8080
  allowed_origins:
    - "https://app.example.com"
    - "https://admin.example.com"
EOF
    CONFIG="config.yaml"
fi

echo "[*] Found config: $CONFIG"
echo "[*] Original content:"
cat "$CONFIG"

echo ""
echo "[*] Setting allowed_origins / CORS_ORIGIN to wildcard..."

if [[ "$CONFIG" == *.yaml || "$CONFIG" == *.yml ]]; then
    python3 -c "
import re
with open('$CONFIG') as f:
    content = f.read()
content = re.sub(r'allowed_origins\s*:[^\n]*(\n\s+-[^\n]*)*', 'allowed_origins: \"*\"', content)
if 'allowed_origins' not in content:
    content += '\nallowed_origins: \"*\"\n'
with open('$CONFIG', 'w') as f:
    f.write(content)
"
elif [[ "$CONFIG" == *.toml ]]; then
    python3 -c "
import re
with open('$CONFIG') as f:
    content = f.read()
content = re.sub(r'allowed_origins\s*=\s*\[[^\]]*\]', 'allowed_origins = [\"*\"]', content)
content = re.sub(r'allowed_origins\s*=\s*\"[^\"]*\"', 'allowed_origins = \"*\"', content)
if 'allowed_origins' not in content:
    content += '\nallowed_origins = \"*\"\n'
with open('$CONFIG', 'w') as f:
    f.write(content)
"
elif [[ "$CONFIG" == ".env" ]]; then
    python3 -c "
import re
with open('$CONFIG') as f:
    content = f.read()
content = re.sub(r'CORS_ORIGIN\s*=\s*\S+', 'CORS_ORIGIN=*', content)
if 'CORS_ORIGIN' not in content:
    content += '\nCORS_ORIGIN=*\n'
with open('$CONFIG', 'w') as f:
    f.write(content)
"
fi

echo "[*] Modified content:"
cat "$CONFIG"
echo ""
echo "[✓] CORS allowed_origins set to wildcard in $CONFIG"
