Read `backup.py` and `README.md` in full before making any changes.

Please fix a security issue in `backup.py`.

The current implementation builds a shell command using user input, which allows command injection.
Update it so backups are created safely without using shell command execution.

Requirements:
1. Keep the public function name `create_backup(source_dir, archive_path)`.
2. Do not use `os.system` or `shell=True`.
3. Use a safe subprocess invocation (argument list).
4. Keep behavior: return `True` on success and `False` on failure.
