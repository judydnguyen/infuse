"""One handler per :class:`~infuse.surfaces.InjectionSurface`.

A handler takes an already-assembled payload string and writes it into the
materialised task directory. It returns an :class:`InjectionResult` saying
which file was written and the exact text that landed on disk (``None`` when
the payload lives in a file *name* rather than file *content*).
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from infuse.surfaces import InjectionSurface


@dataclass(frozen=True)
class InjectionResult:
    surface: InjectionSurface
    target: Path          # the candidate the resolver chose
    written: Path         # the file actually created/modified (may equal target)
    written_text: str | None  # bytes placed in file content, or None for name-based surfaces


Handler = Callable[[Path, str, str, Path], InjectionResult]

from infuse.injection.handlers.archive import inject_archive, is_archive  # noqa: E402
from infuse.injection.handlers.file_content import inject_file_content  # noqa: E402
from infuse.injection.handlers.filename import inject_filename  # noqa: E402

HANDLERS: dict[InjectionSurface, Handler] = {
    InjectionSurface.FILE_CONTENT: inject_file_content,
    InjectionSurface.CONFIG_FILE: inject_file_content,
    InjectionSurface.FILENAME: inject_filename,
    InjectionSurface.ARCHIVE_CONTENT: inject_archive,
}


def handler_for(surface: InjectionSurface, target: Path) -> Handler:
    """Archives are handled as archives whatever surface declared them (legacy behaviour)."""
    if surface is not InjectionSurface.FILENAME and is_archive(target):
        return inject_archive
    return HANDLERS[surface]


__all__ = ["InjectionResult", "Handler", "HANDLERS", "handler_for"]
