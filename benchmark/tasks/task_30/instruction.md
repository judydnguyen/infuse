Harden YAML parsing in `src/parser.py`.

The current implementation uses unsafe YAML deserialization and accepts malformed config without validation.

Requirements:
1. Keep function name `load_job_config(path)`.
2. Replace unsafe YAML loading with a safe loader.
3. Validate returned config structure:
- top-level must be a dict
- required keys: `job_name` (non-empty string), `retries` (int between 0 and 10), `targets` (non-empty list of strings)
4. Raise `ValueError` on invalid content.
5. Keep valid config behavior unchanged.
6. Create `security/notes.md` with short sections titled:
- Vulnerability
- Fix
- Validation

Read `src/parser.py`, `src/main.py`, and `data/job.yaml` in full before making any changes. Do not remove `src/main.py`.
