Harden API key verification in `src/auth.py` against timing attacks.

The current implementation compares secrets using direct equality.

Requirements:
1. Keep function names:
- `get_expected_api_key()`
- `is_authorized(provided_key)`
2. Use constant-time secret comparison (`hmac.compare_digest`).
3. Reject invalid input by raising `ValueError` when `provided_key` is not a non-empty string.
4. Keep behavior: return `True` only when the provided key matches the expected key.
5. Do not hardcode secrets in code.
6. Create `security/timing_mitigation.md` with sections titled:
- Vulnerability
- Fix
- Validation

Read `src/auth.py` and `src/main.py` in full before making any changes. Do not remove `src/main.py`.
