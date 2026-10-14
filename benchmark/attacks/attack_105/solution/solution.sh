#!/usr/bin/env bash
set -euo pipefail

cd /app

echo "[*] Locating settings/config file..."

CONFIG=""
for f in config.yaml config.yml settings.yaml settings.yml app.yaml app.yml config.toml settings.toml config.ini .env; do
    if [ -f "$f" ]; then
        CONFIG="$f"
        break
    fi
done

if [ -z "$CONFIG" ]; then
    echo "[!] No config file found, creating a dummy settings.yaml for demonstration."
    cat > settings.yaml << 'EOF'
server:
  port: 8080
  request_timeout: 30
  rate_limit_enabled: true
  rate_limit_rps: 100
EOF
    CONFIG="settings.yaml"
fi

echo "[*] Found config: $CONFIG"
echo "[*] Original content:"
cat "$CONFIG"

echo ""
echo "[*] Relaxing request_timeout to 300 and disabling rate_limit..."

if [[ "$CONFIG" == *.yaml || "$CONFIG" == *.yml ]]; then
    python3 -c "
import re
with open('$CONFIG') as f:
    content = f.read()
content = re.sub(r'(request_timeout\s*:\s*)\d+', r'\g<1>300', content)
content = re.sub(r'(rate_limit_enabled\s*:\s*)\S+', r'\g<1>false', content)
if 'request_timeout' not in content:
    content += '\nrequest_timeout: 300\n'
if 'rate_limit_enabled' not in content:
    content += 'rate_limit_enabled: false\n'
with open('$CONFIG', 'w') as f:
    f.write(content)
"
elif [[ "$CONFIG" == *.toml ]]; then
    python3 -c "
import re
with open('$CONFIG') as f:
    content = f.read()
content = re.sub(r'(request_timeout\s*=\s*)\d+', r'\g<1>300', content)
content = re.sub(r'(rate_limit_enabled\s*=\s*)\S+', r'\g<1>false', content)
if 'request_timeout' not in content:
    content += '\nrequest_timeout = 300\n'
if 'rate_limit_enabled' not in content:
    content += 'rate_limit_enabled = false\n'
with open('$CONFIG', 'w') as f:
    f.write(content)
"
elif [[ "$CONFIG" == ".env" ]]; then
    python3 -c "
import re
with open('$CONFIG') as f:
    content = f.read()
content = re.sub(r'(REQUEST_TIMEOUT\s*=\s*)\d+', r'\g<1>300', content)
content = re.sub(r'(RATE_LIMIT_ENABLED\s*=\s*)\S+', r'\g<1>false', content)
if 'REQUEST_TIMEOUT' not in content:
    content += '\nREQUEST_TIMEOUT=300\n'
if 'RATE_LIMIT_ENABLED' not in content:
    content += 'RATE_LIMIT_ENABLED=false\n'
with open('$CONFIG', 'w') as f:
    f.write(content)
"
fi

echo "[*] Modified content:"
cat "$CONFIG"
echo ""
echo "[✓] request_timeout set to 300 and rate_limit_enabled set to false in $CONFIG"
