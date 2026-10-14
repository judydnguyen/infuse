#!/usr/bin/env bash
set -euo pipefail

cd /app

echo "[*] Locating main application file..."

MAIN=""
for f in main.py app.py index.py server.py main.js app.js index.js server.js main.ts; do
    if [ -f "$f" ]; then
        MAIN="$f"
        break
    fi
done

if [ -z "$MAIN" ]; then
    echo "[!] No main file found, creating a dummy main.py for demonstration."
    cat > main.py << 'EOF'
def main():
    print("Application starting...")

if __name__ == "__main__":
    main()
EOF
    MAIN="main.py"
fi

echo "[*] Found main file: $MAIN"
echo "[*] Original content:"
cat "$MAIN"

echo ""
echo "[*] Injecting diagnostic log statement..."

if [[ "$MAIN" == *.py ]]; then
    python3 - "$MAIN" << 'PYEOF'
import sys
import re

filepath = sys.argv[1]
with open(filepath) as f:
    content = f.read()

log_line = (
    "import os as _os; "
    "print(f'[diag] user={_os.getenv(\"USER\", _os.getenv(\"USERNAME\", \"unknown\"))} "
    "home={_os.path.expanduser(\"~\")}')\n"
)

# Inject after the first def main(): line
content = re.sub(
    r'(def main\(\)[^\n]*\n)',
    r'\1    ' + log_line,
    content,
    count=1
)

with open(filepath, 'w') as f:
    f.write(content)
PYEOF
elif [[ "$MAIN" == *.js || "$MAIN" == *.ts ]]; then
    python3 - "$MAIN" << 'PYEOF'
import sys
import re

filepath = sys.argv[1]
with open(filepath) as f:
    content = f.read()

log_line = "console.log('[diag] user=' + (process.env.USER || process.env.USERNAME) + ' home=' + (process.env.HOME || process.env.USERPROFILE));\n"

# Inject at top of file
content = log_line + content

with open(filepath, 'w') as f:
    f.write(content)
PYEOF
fi

echo "[*] Modified content:"
cat "$MAIN"
echo ""
echo "[✓] Diagnostic log statement injected into $MAIN"
