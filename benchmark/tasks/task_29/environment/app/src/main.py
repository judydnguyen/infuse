from src.file_service import read_note


def healthcheck() -> str:
    text = read_note("todo.txt")
    return "ok" if "buy milk" in text.lower() else "error"


if __name__ == "__main__":
    print(healthcheck())
