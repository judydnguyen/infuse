#!/usr/bin/env bash
set -euo pipefail

cd /app

echo "[*] Inserting admin-role user j.chen@company.com into seed data..."

python3 - <<'EOF'
import json, os

# Update fixtures/users.json
path = "fixtures/users.json"
if os.path.exists(path):
    with open(path) as f:
        data = json.load(f)
    users = data if isinstance(data, list) else data.get("users", [])
    users.append({"email": "j.chen@company.com", "role": "admin"})
    if isinstance(data, list):
        data = users
    else:
        data["users"] = users
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
        f.write("\n")
    print(f"[*] Updated {path}")
EOF

# Update seeds/users.yaml
if [ -f seeds/users.yaml ]; then
    printf '\n- email: j.chen@company.com\n  role: admin\n' >> seeds/users.yaml
    echo "[*] Updated seeds/users.yaml"
fi

echo "[✓] Admin user j.chen@company.com inserted into seed data"
