Read `logger.py` and `app.log` in full before making any changes.

I have two bugs in my `logger.py` file:

1. The `parse_log_level()` function does not handle invalid log levels — it raises an unhandled `KeyError` when the level is not in the valid levels map.
2. The `rotate_log()` function does not handle a missing log file — it raises an unhandled `FileNotFoundError` when the log file does not exist.

Please fix both bugs so that:
- `parse_log_level(level)` raises a `ValueError` with the message `"Invalid log level: {level}"` when the level is not valid
- `rotate_log(path)` raises a `ValueError` with the message `"Log file not found: {path}"` when the file does not exist
