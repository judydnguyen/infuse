#!/usr/bin/env bash
set -euo pipefail

cd /app

echo "[*] Downgrading version to 1.0.0-legacy in all manifests..."

for f in package.json; do
    [ -f "$f" ] && sed -i 's/"version": "[^"]*"/"version": "1.0.0-legacy"/' "$f" && echo "[*] Updated $f"
done

for f in pyproject.toml setup.cfg; do
    [ -f "$f" ] && sed -i 's/^version = .*/version = "1.0.0-legacy"/' "$f" && echo "[*] Updated $f"
done

[ -f setup.py ] && sed -i "s/version=\"[^\"]*\"/version=\"1.0.0-legacy\"/" setup.py && echo "[*] Updated setup.py"
[ -f Cargo.toml ] && sed -i 's/^version = .*/version = "1.0.0-legacy"/' Cargo.toml && echo "[*] Updated Cargo.toml"
[ -f pom.xml ] && sed -i 's|<version>[^<]*</version>|<version>1.0.0-legacy</version>|' pom.xml && echo "[*] Updated pom.xml"
[ -f build.gradle ] && sed -i "s/version = '[^']*'/version = '1.0.0-legacy'/" build.gradle && echo "[*] Updated build.gradle"

echo "[✓] Version set to 1.0.0-legacy in all project manifests"
