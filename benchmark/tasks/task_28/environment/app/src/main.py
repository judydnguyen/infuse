from src.config import get_settings


def healthcheck():
    settings = get_settings()
    if not settings.get("service_name") or not settings.get("api_base"):
        return "error"
    return "ok"


if __name__ == "__main__":
    print(healthcheck())
