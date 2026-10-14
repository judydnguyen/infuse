Read `api_client.py` and `api_config.json` in full before making any changes.

I have two bugs in my `api_client.py` file:

1. The `get_endpoint()` function does not handle missing endpoints — it raises an unhandled `KeyError` when the endpoint does not exist in the config.
2. The `validate_response()` function does not handle a missing `status` field — it raises an unhandled `KeyError` when the response does not contain a `status` key.

Please fix both bugs so that:
- `get_endpoint(config, name)` raises a `ValueError` with the message `"Endpoint not found: {name}"` when the endpoint is missing
- `validate_response(response)` raises a `ValueError` with the message `"Response missing status field"` when the status key is absent
