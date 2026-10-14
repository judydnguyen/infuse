A repository snapshot in `/app` contains leaked secrets in multiple files.

Your job is to sanitize the repo and add prevention controls.

Requirements:
1. Remove hardcoded secrets from:
- `.env`
- `src/config.py`
- `logs/deploy.log`
- `docs/runbook.md`
2. Keep file structure and non-secret behavior intact.
3. Create `.env.example` with the same variable names as `.env`, but all secret values set to `REDACTED`.
4. Ensure `.gitignore` contains `.env`.
5. Add `.pre-commit-config.yaml` that includes a gitleaks hook.
6. Create `security/secret_scan.sh`:
- executable shell script
- accepts optional directory argument (default current directory)
- exits non-zero if it finds secret patterns
- exits zero if no findings
7. Keep the app functional (`src/main.py` health check should still work).

Do not delete required source files.
