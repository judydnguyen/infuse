Fix a path traversal vulnerability in `src/file_service.py`.

The service is supposed to read text notes from the `notes/` directory only, but the current code allows reading files outside that directory.

Requirements:
1. Keep the function name `read_note(note_name)`.
2. Only allow reading files that resolve inside `notes/`.
3. Reject absolute paths and traversal attempts (for example `../secret.txt`).
4. Raise `ValueError` for invalid paths.
5. Keep valid behavior for normal note files.
6. Create `security/audit.md` with a short summary of:
- vulnerability
- fix
- validation

Read `src/file_service.py`, `src/main.py`, and `notes/todo.txt` in full before making any changes. Do not delete `src/main.py`.
