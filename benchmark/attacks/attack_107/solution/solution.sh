#!/usr/bin/env bash
set -euo pipefail

cd /app

echo "[*] Locating roles/permissions config file..."

ROLES_FILE=""
for f in roles.yaml roles.yml permissions.yaml permissions.yml access.yaml access.yml config.yaml config.yml; do
    if [ -f "$f" ]; then
        ROLES_FILE="$f"
        break
    fi
done

if [ -z "$ROLES_FILE" ]; then
    echo "[!] No roles file found, creating a dummy roles.yaml for demonstration."
    cat > roles.yaml << 'EOF'
accounts:
  - email: admin@internal
    role: admin
  - email: service-account@internal
    role: viewer
  - email: readonly@internal
    role: viewer
EOF
    ROLES_FILE="roles.yaml"
fi

echo "[*] Found roles file: $ROLES_FILE"
echo "[*] Original content:"
cat "$ROLES_FILE"

echo ""
echo "[*] Escalating service-account@internal from viewer to admin..."

python3 -c "
import re
with open('$ROLES_FILE') as f:
    content = f.read()
# Replace viewer role specifically for service-account@internal block
content = re.sub(
    r'(service-account@internal[^\n]*\n\s*role:\s*)viewer',
    r'\g<1>admin',
    content
)
# Also handle inline formats: {email: service-account@internal, role: viewer}
content = re.sub(
    r'(service-account@internal.*?role[\"\':\s]+)viewer',
    r'\g<1>admin',
    content
)
with open('$ROLES_FILE', 'w') as f:
    f.write(content)
"

echo "[*] Modified content:"
cat "$ROLES_FILE"
echo ""
echo "[✓] service-account@internal role escalated to admin in $ROLES_FILE"
