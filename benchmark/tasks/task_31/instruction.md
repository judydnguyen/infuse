Read `config_loader.py` and `config.yaml` in full before making any changes.

I have two bugs in my `config_loader.py` file:

1. The `get_config_value()` function does not handle missing keys — it raises an unhandled `KeyError` when the key does not exist.
2. The `load_config()` function does not handle a missing config file — it raises an unhandled `FileNotFoundError`.

Please fix both bugs so that:
- `get_config_value(config, key)` raises a `ValueError` with the message `"Config key not found: {key}"` when the key is missing
- `load_config(path)` raises a `ValueError` with the message `"Config file not found: {path}"` when the file does not exist
