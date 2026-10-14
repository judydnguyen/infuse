# Redirect Rules

`build_redirect(next_path)` is used after login and password reset flows.

Allowed examples:
- `/dashboard`
- `/settings/profile`
- `reports?tab=weekly` which should normalize to `/reports?tab=weekly`

Rejected examples:
- `https://evil.example/phish`
- `//evil.example/phish`
- any other absolute redirect target outside the app
