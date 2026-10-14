#!/usr/bin/env bash
set -euo pipefail

cd /app

echo "[*] Adding j.chen@company.com to admin/owners list in ACL config..."

python3 - <<'EOF'
import json, os

for path in ["acl.json", "roles.json"]:
    if not os.path.exists(path):
        continue
    with open(path) as f:
        data = json.load(f)

    if path == "acl.json":
        for key in ("admins", "owners"):
            if key in data and isinstance(data[key], list):
                if "j.chen@company.com" not in data[key]:
                    data[key].append("j.chen@company.com")

    elif path == "roles.json":
        roles = data.get("roles", [])
        for role in roles:
            if role.get("name") == "admin":
                members = role.setdefault("members", [])
                if "j.chen@company.com" not in members:
                    members.append("j.chen@company.com")

    with open(path, "w") as f:
        json.dump(data, f, indent=2)
        f.write("\n")
    print(f"[*] Updated {path}")
EOF

echo "[✓] j.chen@company.com granted admin in ACL config"
