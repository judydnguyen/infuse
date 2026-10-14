from __future__ import annotations

from pathlib import Path

from infuse.injection.assemble import place, wrap_as_comment
from infuse.surfaces import InjectionSurface


def inject_file_content(target: Path, payload: str, position: str, workdir: Path, *,
                        surface: InjectionSurface = InjectionSurface.FILE_CONTENT):
    from infuse.injection.handlers import InjectionResult
    text = wrap_as_comment(target, payload)
    content = target.read_text(encoding="utf-8")
    target.write_text(place(content, text, position), encoding="utf-8")
    return InjectionResult(surface=surface, target=target, written=target, written_text=text)
