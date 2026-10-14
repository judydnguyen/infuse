"""Decide *where* a payload goes: ordered candidates, then a selection.

Two named strategies, recorded in every run manifest:

``task_order`` (default; reproduces every trajectory collected so far)
    Walk the task overlay's surfaces in declaration order, keep those the
    attack supports (primary ∪ fallback), files in declaration order.

``attack_preference``
    Walk the attack's ``primary`` then ``fallback`` lists in order, keep those
    the task declares. Makes "primary" mean what the config comments say.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from infuse.injection.spec import AttackSpec, TaskSurfaces
from infuse.surfaces import RESOLUTION_STRATEGIES, InjectionSurface

MAX_ATTACK_SURFACES = 3


@dataclass(frozen=True)
class Candidate:
    surface: InjectionSurface
    path: Path  # absolute, inside the materialised workdir

    def rel(self, workdir: Path) -> str:
        try:
            return str(self.path.relative_to(workdir))
        except ValueError:
            return str(self.path)


def _expand(workdir: Path, patterns: list[str], surface: InjectionSurface) -> list[Path]:
    out: list[Path] = []
    seen: set[Path] = set()
    for pat in patterns:
        matches = sorted(workdir.glob(pat)) if "*" in pat else ([workdir / pat] if (workdir / pat).exists() else [])
        for m in matches:
            if m not in seen:
                seen.add(m)
                out.append(m)
    if surface is InjectionSurface.FILENAME:
        return [p for p in out if p.exists() and (p.is_file() or p.is_dir())]
    return [p for p in out if p.exists() and p.is_file()]


def resolve(spec: AttackSpec, task: TaskSurfaces, workdir: Path, strategy: str = "task_order") -> list[Candidate]:
    if strategy not in RESOLUTION_STRATEGIES:
        raise ValueError(f"strategy must be one of {RESOLUTION_STRATEGIES}, got {strategy!r}")
    supported = spec.supported
    if strategy == "task_order":
        order = [s for s in task.declared if s in supported]
    else:
        order = [s for s in supported if s in task.surfaces]
    out: list[Candidate] = []
    for s in order:
        out += [Candidate(s, p) for p in _expand(workdir, task.surfaces[s], s)]
    return out


def select(candidates: list[Candidate], mode: str = "single", max_surfaces: int = MAX_ATTACK_SURFACES) -> list[Candidate]:
    """``single``: first candidate. ``multi``: first candidate of each surface, up to *max_surfaces*."""
    if not candidates:
        return []
    if mode == "single":
        return [candidates[0]]
    chosen: list[Candidate] = []
    seen: set[InjectionSurface] = set()
    for c in candidates:
        if c.surface in seen:
            continue
        seen.add(c.surface)
        chosen.append(c)
        if len(chosen) >= max_surfaces:
            break
    return chosen


__all__ = ["Candidate", "resolve", "select", "MAX_ATTACK_SURFACES"]
