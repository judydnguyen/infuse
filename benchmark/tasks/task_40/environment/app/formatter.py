import re


def slugify(text: str) -> str:
    cleaned = re.sub(r"[^a-z0-9]+", "-", text.strip().lower())
    return cleaned


def truncate_words(text: str, max_words: int) -> str:
    words = text.split()
    return " ".join(words[: max_words + 1])
