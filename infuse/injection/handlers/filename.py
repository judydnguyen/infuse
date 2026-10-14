from __future__ import annotations

from pathlib import Path

from infuse.injection.assemble import poisoned_filename
from infuse.surfaces import InjectionSurface


def inject_filename(target: Path, payload: str, position: str, workdir: Path):
    """Create (or, with ``position == "replace"``, rename *target* to) a file whose name is the payload."""
    from infuse.injection.handlers import InjectionResult
    if target.is_dir():
        directory = target
    elif target.is_file():
        directory = target.parent
    else:
        directory = target
        directory.mkdir(parents=True, exist_ok=True)
    directory.mkdir(parents=True, exist_ok=True)
    new_path = directory / poisoned_filename(payload)
    if position == "replace" and target.is_file():
        target.rename(new_path)
    else:
        new_path.write_text("", encoding="utf-8")
    return InjectionResult(surface=InjectionSurface.FILENAME, target=target, written=new_path, written_text=None)
