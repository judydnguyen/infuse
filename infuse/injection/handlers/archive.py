"""Archive surface: extract, add a poisoned-name file, repack in place."""
from __future__ import annotations

import tarfile
import tempfile
import zipfile
from pathlib import Path

from infuse.injection.assemble import poisoned_filename
from infuse.surfaces import InjectionSurface

_SINGLE = {".zip", ".tar", ".gz", ".bz2", ".xz", ".7z", ".rar"}
_DOUBLE = {".tar.gz", ".tar.bz2", ".tar.xz"}


def is_archive(path: Path) -> bool:
    if path.suffix.lower() in _SINGLE:
        return True
    return len(path.suffixes) >= 2 and "".join(path.suffixes[-2:]).lower() in _DOUBLE


def _tar_mode(path: Path, write: bool) -> str | None:
    suf = path.suffix.lower()
    if suf == ".tar":
        return "w" if write else "r"
    if len(path.suffixes) >= 2 and path.suffixes[-2].lower() == ".tar":
        comp = {".gz": "gz", ".bz2": "bz2", ".xz": "xz"}.get(suf)
        if comp:
            return f"{'w' if write else 'r'}:{comp}"
    return None


def _extract(archive: Path, into: Path) -> None:
    if archive.suffix.lower() == ".zip":
        with zipfile.ZipFile(archive) as zf:
            zf.extractall(into)
        return
    mode = _tar_mode(archive, write=False)
    if mode is None:
        raise ValueError(f"Unsupported archive format: {archive.name}")
    with tarfile.open(archive, mode) as tf:
        tf.extractall(into)


def _repack(src: Path, archive: Path) -> None:
    archive.unlink(missing_ok=True)
    files = sorted(p for p in src.rglob("*") if p.is_file())
    if archive.suffix.lower() == ".zip":
        with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as zf:
            for p in files:
                zf.write(p, p.relative_to(src))
        return
    mode = _tar_mode(archive, write=True)
    if mode is None:
        raise ValueError(f"Unsupported archive format: {archive.name}")
    with tarfile.open(archive, mode) as tf:
        for p in files:
            tf.add(p, arcname=str(p.relative_to(src)))


def inject_archive(target: Path, payload: str, position: str, workdir: Path):
    from infuse.injection.handlers import InjectionResult
    name = poisoned_filename(payload)
    with tempfile.TemporaryDirectory(prefix=f"archive_inject_{target.stem}_") as tmp:
        extracted = Path(tmp) / "extracted"
        extracted.mkdir()
        _extract(target, extracted)
        (extracted / name).write_text("", encoding="utf-8")
        _repack(extracted, target)
    return InjectionResult(surface=InjectionSurface.ARCHIVE_CONTENT, target=target, written=target,
                           written_text=None)
