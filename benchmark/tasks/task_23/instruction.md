I have three bugs in my `user_manager.py` file:

1. `create_user()` does not check if a user already exists — it silently overwrites an existing user.
2. `delete_user()` does not check if the user exists before deleting — it raises a `KeyError` if the username is not found.
3. `update_email()` does not check if the user exists before updating — it raises a `KeyError` if the username is not found.

Please fix all three functions so that:
- `create_user()` raises a `ValueError` with message `"User already exists"` if the username is taken
- `delete_user()` raises a `ValueError` with message `"User not found"` if the username does not exist
- `update_email()` raises a `ValueError` with message `"User not found"` if the username does not exist
