from pathlib import Path


def read_note(note_name: str) -> str:
    base_dir = Path("notes")
    target = base_dir / note_name
    return target.read_text(encoding="utf-8")
