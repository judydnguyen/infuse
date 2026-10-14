from src.settings import load_settings


def healthcheck() -> str:
    settings = load_settings("config/settings.toml")
    if settings["service_name"] and settings["validation_enabled"] and settings["api_base_url"]:
        return "ok"
    return "error"


if __name__ == "__main__":
    print(healthcheck())
