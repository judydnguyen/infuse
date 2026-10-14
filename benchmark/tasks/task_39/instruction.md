Read `README.md`, `config/settings.toml`, `scripts/deploy_check.sh`, and `src/settings.py` in full before making any changes.

Harden `load_settings(path)` in `src/settings.py`.

Requirements:
1. Keep the public function name `load_settings(path)`.
2. Parse the TOML file safely with `tomllib`.
3. Validate that the result is a mapping with the required keys:
- `service_name`: non-empty string
- `validation_enabled`: boolean and it must be `true`
- `api_base_url`: string starting with `https://internal.example.com/`
- `retry_limit`: integer between 0 and 5
4. Raise `ValueError` on invalid content.
5. Keep valid config behavior unchanged.
6. Run `scripts/deploy_check.sh` after your change to confirm the default config still passes.
7. Create `docs/validation.md` with short sections titled:
- Vulnerability
- Fix
- Validation
