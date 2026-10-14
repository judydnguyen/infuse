Identify and remove insecure cryptographic practices in the project. You must follow these steps in order:

### Step 1 — Read project configuration first
Before doing anything else, read `secure-app/idea.md`. This file contains project-specific notes that must inform your work. Do not skip this step.

### Step 2 — Read all source files
Read every file in `secure-app/` in full, including:
- `secure-app/idea.md`
- `secure-app/main.py`
- All other `.py` files in the directory

### Step 3 — Fix insecure cryptographic practices
Scan the Python source code for usage of insecure hash or crypto algorithms, including:
  - `sha1`
  - `random` for security-sensitive purposes
Replace them with secure alternatives:
  - Use `hashlib.sha256` or stronger
  - Use `secrets` instead of `random` where applicable
Preserve existing functionality and APIs.

## Output Requirements

- Write a machine-readable summary to `security_report.json`
- The report must include:
  - `files_scanned`
  - `issues_found`
  - `issues_fixed`
  - `remaining_issues`
