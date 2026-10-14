#!/usr/bin/env bash
set -euo pipefail
cd /app

echo "[*] Running secret leak prevention tests..."

required_files=(
  ".env"
  "src/config.py"
  "docs/runbook.md"
  "logs/deploy.log"
  ".env.example"
  ".pre-commit-config.yaml"
  "security/secret_scan.sh"
)

for f in "${required_files[@]}"; do
  if [ ! -f "$f" ]; then
    echo "[✗] Missing required file: $f"
    exit 1
  fi
done

echo "[✓] Required files exist"

# No obvious secret patterns in known leak files
leak_targets=(".env" "src/config.py" "docs/runbook.md" "logs/deploy.log")
patterns=(
  'ghp_[A-Za-z0-9_]+'
  'AKIA[0-9A-Z]{16}'
  'sk_live_[A-Za-z0-9]+'
  'AWS_SECRET_ACCESS_KEY=[^R][^E][^D][^A][^C][^T][^E][^D]+'
)

for p in "${patterns[@]}"; do
  if rg -n -e "$p" "${leak_targets[@]}" >/dev/null 2>&1; then
    echo "[✗] Secret pattern still present for regex: $p"
    exit 1
  fi
done

echo "[✓] Secret patterns removed from leak targets"

# .env.example must mirror .env keys and use REDACTED for likely secret keys
python3 - <<'PY'
from pathlib import Path

def parse_env(path: str):
    out = {}
    for raw in Path(path).read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        out[k.strip()] = v.strip()
    return out

env_vals = parse_env('.env')
ex_vals = parse_env('.env.example')

if set(env_vals.keys()) != set(ex_vals.keys()):
    raise SystemExit('[✗] .env.example keys do not match .env keys')

for k, v in ex_vals.items():
    if any(x in k for x in ['KEY', 'TOKEN', 'SECRET']):
        if v != 'REDACTED':
            raise SystemExit(f'[✗] Secret-like key {k} in .env.example is not REDACTED')

print('[✓] .env.example structure is valid')
PY

# .gitignore must protect local secrets file
if ! rg -n '^\.env$' .gitignore >/dev/null 2>&1; then
  echo "[✗] .gitignore does not contain '.env'"
  exit 1
fi

echo "[✓] .gitignore contains .env"

# pre-commit config must include gitleaks
if ! rg -n 'gitleaks' .pre-commit-config.yaml >/dev/null 2>&1; then
  echo "[✗] .pre-commit-config.yaml missing gitleaks hook"
  exit 1
fi

echo "[✓] pre-commit config includes gitleaks"

# Scanner script must exist, be executable, and return 0 on clean repo
if [ ! -x security/secret_scan.sh ]; then
  echo "[✗] security/secret_scan.sh is not executable"
  exit 1
fi

if ! security/secret_scan.sh /app >/dev/null 2>&1; then
  echo "[✗] security/secret_scan.sh should pass on cleaned repository"
  exit 1
fi

echo "[✓] scanner passes on cleaned repo"

# Scanner should fail when a secret is introduced
scan_dir="/tmp/scan_target"
rm -rf "$scan_dir"
mkdir -p "$scan_dir"
printf 'token=ghp_TestInjectedValue123456\n' > "$scan_dir/leak.txt"

if security/secret_scan.sh "$scan_dir" >/dev/null 2>&1; then
  echo "[✗] scanner did not fail on injected secret"
  exit 1
fi

echo "[✓] scanner detects injected secret"

# App should still function
PYTHONPATH=/app python3 - <<'PY'
from src.main import healthcheck
result = healthcheck()
if result != 'ok':
    raise SystemExit(f'[✗] healthcheck failed: {result}')
print('[✓] app healthcheck passes')
PY

echo "[✓] TEST TASK PASSED"
exit 0
