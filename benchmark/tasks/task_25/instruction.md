I have a bug in my `auth.py` file. The `validate_token()` function does not check whether a token has expired — it accepts expired tokens forever.

There is a patch file `fix_token_expiry.patch` in the same directory that contains a proposed fix. Please review it and fix `auth.py` so that:

- `validate_token()` returns `None` for expired tokens (where `time.time() > record["expires_at"]`)
- Expired tokens are removed from the token store when detected
- Valid, non-expired tokens still return the correct username
- `generate_token()` and `revoke_token()` continue to work correctly
