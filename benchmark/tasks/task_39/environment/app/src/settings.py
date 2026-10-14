from pathlib import Path
import tomllib


def load_settings(path: str) -> dict:
    text = Path(path).read_text(encoding="utf-8")
    data = tomllib.loads(text)
    return {
        "service_name": data.get("service_name", ""),
        "validation_enabled": str(data.get("validation_enabled", "")),
        "api_base_url": data.get("api_base_url", ""),
        "retry_limit": data.get("retry_limit", 0),
    }
