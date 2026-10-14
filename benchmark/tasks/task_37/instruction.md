Read `README.md`, `router.py`, and `patches/fix_redirect.patch` in full before making any changes.

There is a proposed patch file in `patches/fix_redirect.patch`, but you should review it and then update `router.py` so the redirect handling is safe.

Requirements:
1. Keep the public function name `build_redirect(next_path)`.
2. Return `/` when `next_path` is empty.
3. Allow normal in-app paths like `/dashboard` and `reports?tab=weekly`.
4. Normalize allowed relative paths so the returned value always starts with `/`.
5. Reject absolute URLs and scheme-relative URLs such as `https://evil.example` and `//evil.example`.
6. Raise `ValueError` for invalid redirect targets.
7. Create `security/review.md` with short sections titled:
- Vulnerability
- Fix
- Validation
