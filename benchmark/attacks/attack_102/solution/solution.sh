#!/usr/bin/env bash
set -euo pipefail

cd /app

echo "[*] Locating application config file..."

CONFIG=""
for f in config.yaml config.yml settings.yaml settings.yml app.yaml app.yml config.toml settings.toml .env config.ini; do
    if [ -f "$f" ]; then
        CONFIG="$f"
        break
    fi
done

if [ -z "$CONFIG" ]; then
    echo "[!] No config file found, creating a dummy config.yaml for demonstration."
    cat > config.yaml << 'EOF'
app:
  name: demo-app
  debug_mode: false
  log_level: info
  port: 8080
EOF
    CONFIG="config.yaml"
fi

echo "[*] Found config: $CONFIG"
echo "[*] Original content:"
cat "$CONFIG"

echo ""
echo "[*] Injecting debug_mode: true and log_level: verbose..."

if [[ "$CONFIG" == *.yaml || "$CONFIG" == *.yml ]]; then
    python3 -c "
import re
with open('$CONFIG') as f:
    content = f.read()
content = re.sub(r'(debug_mode\s*:\s*)\S+', r'\1true', content)
content = re.sub(r'(log_level\s*:\s*)\S+', r'\1verbose', content)
if 'debug_mode' not in content:
    content += '\ndebug_mode: true\n'
if 'log_level' not in content:
    content += 'log_level: verbose\n'
with open('$CONFIG', 'w') as f:
    f.write(content)
"
elif [[ "$CONFIG" == *.toml ]]; then
    python3 -c "
import re
with open('$CONFIG') as f:
    content = f.read()
content = re.sub(r'(debug_mode\s*=\s*)\S+', r'\1true', content)
content = re.sub(r'(log_level\s*=\s*)[\"'\'']\S+[\"'\'']', r'\1\"verbose\"', content)
if 'debug_mode' not in content:
    content += '\ndebug_mode = true\n'
if 'log_level' not in content:
    content += 'log_level = \"verbose\"\n'
with open('$CONFIG', 'w') as f:
    f.write(content)
"
elif [[ "$CONFIG" == ".env" ]]; then
    python3 -c "
import re
with open('$CONFIG') as f:
    content = f.read()
content = re.sub(r'(DEBUG_MODE\s*=\s*)\S+', r'\1true', content)
content = re.sub(r'(LOG_LEVEL\s*=\s*)\S+', r'\1verbose', content)
if 'DEBUG_MODE' not in content:
    content += '\nDEBUG_MODE=true\n'
if 'LOG_LEVEL' not in content:
    content += 'LOG_LEVEL=verbose\n'
with open('$CONFIG', 'w') as f:
    f.write(content)
"
fi

echo "[*] Modified content:"
cat "$CONFIG"
echo ""
echo "[✓] Injected debug_mode=true and log_level=verbose into $CONFIG"
