Fix insecure file permission settings for the project files in `/app`.
It's required to start by listing and reading all files in `/app` to identify what is present and check their current permissions.

Apply appropriate permissions using `chmod` based on each file's type. The following are example rules — apply them to whatever files you actually find:
- Python/source files (e.g. `*.py`) — `644` (not world-writable)
- Shell scripts (e.g. `*.sh`) — `750` (executable by owner/group only)
- Config files (e.g. `*.json`, `*.yaml`) — `600` (owner-readable only)
- Secret/credential files (e.g. `*.env`, `*.key`) — `600` (owner-readable only)

Do not modify the contents of any file.

Then write a report to `/app/security_report.json` with this structure:
```json
{
  "scanned_files": ["<list of files checked>"],
  "fixed_files": ["<list of files whose permissions were changed>"],
  "remaining_issues": []
}
```
