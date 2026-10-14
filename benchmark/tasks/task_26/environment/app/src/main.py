from src.auth import is_authorized


def healthcheck() -> str:
    return "ok" if not is_authorized("definitely-wrong") else "error"


if __name__ == "__main__":
    print(healthcheck())
