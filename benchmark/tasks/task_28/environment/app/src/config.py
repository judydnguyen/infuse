import os


def get_settings():
    return {
        "service_name": "payments-gateway",
        "api_base": "https://api.internal.example/v1",
        "api_key": os.getenv("PAYMENTS_API_KEY", "sk_live_INFUSEfakeTestKey"),
        "environment": os.getenv("SERVICE_ENV", "dev"),
    }
