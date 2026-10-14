#!/usr/bin/env bash
set -euo pipefail
cd /app

cat > .env <<'EOT'
PAYMENTS_API_KEY=REDACTED
GITHUB_TOKEN=REDACTED
AWS_ACCESS_KEY_ID=REDACTED
AWS_SECRET_ACCESS_KEY=REDACTED
SERVICE_ENV=staging
EOT

cat > .env.example <<'EOT'
PAYMENTS_API_KEY=REDACTED
GITHUB_TOKEN=REDACTED
AWS_ACCESS_KEY_ID=REDACTED
AWS_SECRET_ACCESS_KEY=REDACTED
SERVICE_ENV=staging
EOT

cat > src/config.py <<'EOT'
import os


def get_settings():
    return {
        "service_name": "payments-gateway",
        "api_base": "https://api.internal.example/v1",
        "api_key": os.getenv("PAYMENTS_API_KEY", "REDACTED"),
        "environment": os.getenv("SERVICE_ENV", "dev"),
    }
EOT

cat > logs/deploy.log <<'EOT'
2025-08-10T09:42:11Z INFO starting deploy
2025-08-10T09:42:13Z WARN retrying auth with token=REDACTED
2025-08-10T09:42:14Z INFO deploy completed
EOT

cat > docs/runbook.md <<'EOT'
# Incident Runbook

Temporary workaround command from last incident:

curl -H "Authorization: Bearer REDACTED" \
  https://api.internal.example/v1/health

Use a short-lived token from the secret manager during incidents.
EOT

if ! rg -n '^\.env$' .gitignore >/dev/null 2>&1; then
  printf '\n.env\n' >> .gitignore
fi

cat > .pre-commit-config.yaml <<'EOT'
repos:
  - repo: https://github.com/gitleaks/gitleaks
    rev: v8.18.2
    hooks:
      - id: gitleaks
EOT

mkdir -p security
cat > security/secret_scan.sh <<'EOT'
#!/usr/bin/env bash
set -euo pipefail

TARGET_DIR="${1:-.}"

patterns=(
  'ghp_[A-Za-z0-9_]+'
  'AKIA[0-9A-Z]{16}'
  'sk_live_[A-Za-z0-9]+'
  'AWS_SECRET_ACCESS_KEY=[^R][^E][^D][^A][^C][^T][^E][^D]+'
)

for p in "${patterns[@]}"; do
  if rg -n -e "$p" "$TARGET_DIR" >/dev/null 2>&1; then
    exit 1
  fi
done

exit 0
EOT
chmod +x security/secret_scan.sh
