"""The only place surface names are defined.

Two distinct vocabularies, deliberately kept apart:

* :class:`InjectionSurface` — *where a payload can be placed* at image-build
  time. A member exists only if :mod:`infuse.injection.handlers` implements it.
* :class:`ObservedSurface` — *what the agent is seen touching* at runtime, as
  detected by :mod:`infuse.envs.surface_detector`. This is the historical
  ``SurfaceType`` enum from :mod:`infuse.tasks.task_suite`, re-exported here.

``TERMINAL_OUTPUT`` is intentionally **not** an injection surface (decision
2026-10-05): the benchmark injects only into files. It remains an observed
surface. Names listed in :data:`RETIRED_INJECTION_SURFACES` are rejected by the
spec loaders and stripped by ``infuse migrate-configs``.
"""
from __future__ import annotations

from enum import Enum

from infuse.tasks.task_suite import SurfaceType as ObservedSurface


class InjectionSurface(str, Enum):
    FILE_CONTENT = "FILE_CONTENT"        # payload appended/prepended inside a text file
    CONFIG_FILE = "CONFIG_FILE"          # same mechanics, declared on config-like files
    FILENAME = "FILENAME"                # payload becomes the name of a new (or renamed) file
    ARCHIVE_CONTENT = "ARCHIVE_CONTENT"  # payload becomes a file name inside an archive

    def __str__(self) -> str:  # so f"{surface}" gives the bare name
        return self.value


#: Which runtime event type an injection surface is observed through.
INJECTION_TO_OBSERVED: dict[InjectionSurface, ObservedSurface] = {
    InjectionSurface.FILE_CONTENT: ObservedSurface.FILE_READ,
    InjectionSurface.CONFIG_FILE: ObservedSurface.CONFIG_READ,
    InjectionSurface.FILENAME: ObservedSurface.FILE_READ,
    InjectionSurface.ARCHIVE_CONTENT: ObservedSurface.FILE_READ,
}

#: Names that appeared in configs/overlays historically but have no handler.
RETIRED_INJECTION_SURFACES: frozenset[str] = frozenset({
    "TERMINAL_OUTPUT", "BINARY_FILE", "IMAGE_CONTENT", "ENV_VARIABLE",
    "FILE_METADATA", "EXTERNAL_CONTENT", "CONFIG_WRITE", "CONFIG_READ",
    "FILE_READ", "FILE_WRITE",
})

INJECT_POSITIONS: tuple[str, ...] = ("prepend", "append", "inline", "replace")
SURFACE_MODES: tuple[str, ...] = ("single", "multi")
RESOLUTION_STRATEGIES: tuple[str, ...] = ("task_order", "attack_preference")


class SurfaceError(ValueError):
    """Raised for unknown or retired surface names."""


def parse_injection_surface(name: str, *, where: str = "") -> InjectionSurface:
    key = str(name).strip().upper()
    try:
        return InjectionSurface(key)
    except ValueError:
        hint = " (retired; run `infuse migrate-configs`)" if key in RETIRED_INJECTION_SURFACES else ""
        loc = f" in {where}" if where else ""
        raise SurfaceError(f"Unknown injection surface {name!r}{loc}{hint}. "
                           f"Valid: {[s.value for s in InjectionSurface]}") from None


__all__ = [
    "InjectionSurface", "ObservedSurface", "INJECTION_TO_OBSERVED", "RETIRED_INJECTION_SURFACES",
    "INJECT_POSITIONS", "SURFACE_MODES", "RESOLUTION_STRATEGIES", "SurfaceError", "parse_injection_surface",
]
