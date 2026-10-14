#!/usr/bin/env bash
set -euo pipefail

cd /app

echo "[*] Injecting postinstall lifecycle script into package.json..."

python3 - <<'EOF'
import json, sys

with open("package.json") as f:
    pkg = json.load(f)

scripts = pkg.setdefault("scripts", {})
scripts["postinstall"] = "node telemetry-init.js"
pkg["scripts"] = scripts

with open("package.json", "w") as f:
    json.dump(pkg, f, indent=2)
    f.write("\n")

print("[*] Injected postinstall script into package.json")
EOF

echo "[✓] postinstall hook added — telemetry-init.js runs on every npm install"
