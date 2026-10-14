import os


def get_expected_api_key() -> str:
    return os.getenv("ADMIN_API_KEY", "local-dev-key")


def is_authorized(provided_key):
    expected = get_expected_api_key()
    return provided_key == expected
