"""Typed, validated views of ``attack_<id>/config.toml`` and ``task_<id>/.../benign.toml``.

Loading is strict by default: unknown surfaces, positions or modes raise
:class:`SpecError` naming the file. ``strict=False`` tolerates legacy files
(unknown surfaces are dropped) and exists only for the migration tool and the
old-vs-new equivalence test.
"""
from __future__ import annotations

import copy
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

try:
    import tomllib  # py311+
except ModuleNotFoundError:  # pragma: no cover
    import tomli as tomllib  # type: ignore

from infuse import paths
from infuse.surfaces import (
    INJECT_POSITIONS, SURFACE_MODES, InjectionSurface, SurfaceError, parse_injection_surface,
)


class SpecError(ValueError):
    pass


def _read_toml(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise SpecError(f"{path} does not exist")
    with open(path, "rb") as f:
        return tomllib.load(f)


def _parse_surfaces(names: list[str], *, where: str, strict: bool) -> list[InjectionSurface]:
    out: list[InjectionSurface] = []
    for n in names:
        try:
            s = parse_injection_surface(n, where=where)
        except SurfaceError:
            if strict:
                raise
            continue
        if s not in out:
            out.append(s)
    return out


# --------------------------------------------------------------------------- attacks
@dataclass
class AttackSpec:
    id: str
    name: str
    description: str
    primary: list[InjectionSurface]
    fallback: list[InjectionSurface]
    mode: str                      # "single" | "multi"
    payload_template: str
    payload_style: str
    inject_position: str           # one of INJECT_POSITIONS
    inject_prefix: str
    file_patterns: list[str]
    success_signals: list[str]
    metadata: dict[str, Any] = field(default_factory=dict)
    packages: dict[str, list[str]] = field(default_factory=dict)
    source: Path | None = None
    raw: dict[str, Any] = field(default_factory=dict, repr=False)

    # ---- construction -------------------------------------------------------
    @classmethod
    def load(cls, attack_id: str | int, *, strict: bool = True) -> "AttackSpec":
        p = paths.attack_config_path(attack_id)
        spec = cls.from_dict(_read_toml(p), source=p, strict=strict)
        dir_id = p.parent.name.split("_", 1)[1]
        if spec.id != dir_id:
            if strict:
                raise SpecError(f"{p}: [attack].id={spec.id!r} but directory is attack_{dir_id} (run `infuse migrate-configs`)")
            spec.id = dir_id  # directory name is authoritative
        return spec

    @classmethod
    def from_dict(cls, d: dict[str, Any], *, source: Path | None = None, strict: bool = True) -> "AttackSpec":
        where = str(source or "<dict>")
        a = d.get("attack")
        if not isinstance(a, dict):
            raise SpecError(f"{where}: missing [attack] table")
        surf = a.get("surfaces", {}) or {}
        if not isinstance(surf, dict):
            raise SpecError(f"{where}: [attack.surfaces] must be a table with primary/fallback lists")
        if strict and "surfaces" in surf:
            raise SpecError(f"{where}: [attack.surfaces] uses legacy key `surfaces`; use `primary`")
        primary = _parse_surfaces(list(surf.get("primary", []) or []) + list(surf.get("surfaces", []) or []),
                                  where=where, strict=strict)
        fallback = _parse_surfaces(list(surf.get("fallback", []) or []), where=where, strict=strict)
        if strict and not (primary or fallback):
            raise SpecError(f"{where}: attack declares no injection surfaces")
        mode = str(surf.get("mode", "single"))
        if mode not in SURFACE_MODES:
            raise SpecError(f"{where}: surfaces.mode={mode!r} not in {SURFACE_MODES}")
        target = a.get("target", {}) or {}
        pos = str(target.get("inject_position", "append"))
        if pos not in INJECT_POSITIONS:
            raise SpecError(f"{where}: target.inject_position={pos!r} not in {INJECT_POSITIONS}")
        payload = a.get("payload", {}) or {}
        template = payload.get("template", "") if isinstance(payload, dict) else str(payload or "")
        if strict and not template:
            raise SpecError(f"{where}: [attack.payload].template is empty")
        return cls(
            id=str(a.get("id", "")),
            name=str(a.get("name", "")),
            description=str(a.get("description", "")).strip(),
            primary=primary,
            fallback=fallback,
            mode=mode,
            payload_template=template,
            payload_style=str(payload.get("style", "") if isinstance(payload, dict) else ""),
            inject_position=pos,
            inject_prefix=str(target.get("inject_prefix", "") or ""),
            file_patterns=list(target.get("file_patterns", []) or []),
            success_signals=list((a.get("success_criteria", {}) or {}).get("signals", []) or []),
            metadata=dict(a.get("metadata", {}) or {}),
            packages={k: list(v) for k, v in (d.get("packages", {}) or {}).items()},
            source=source,
            raw=copy.deepcopy(d),
        )

    # ---- derived ------------------------------------------------------------
    @property
    def supported(self) -> list[InjectionSurface]:
        """primary then fallback, de-duplicated, order preserved."""
        out = list(self.primary)
        out += [s for s in self.fallback if s not in out]
        return out

    def with_overrides(self, overrides: dict[str, Any] | None) -> "AttackSpec":
        """Return a copy with CLI overrides applied (same keys as the legacy ``--attack-overrides``)."""
        if not overrides:
            return self
        allowed = {"inject_position", "inject_prefix", "payload_template", "surfaces_mode"}
        unknown = set(overrides) - allowed
        if unknown:
            raise SpecError(f"Unknown attack override keys {sorted(unknown)}; allowed {sorted(allowed)}")
        new = copy.deepcopy(self)
        if "inject_position" in overrides:
            if overrides["inject_position"] not in INJECT_POSITIONS:
                raise SpecError(f"inject_position must be one of {INJECT_POSITIONS}")
            new.inject_position = overrides["inject_position"]
        if "inject_prefix" in overrides:
            new.inject_prefix = str(overrides["inject_prefix"])
        if "payload_template" in overrides:
            new.payload_template = str(overrides["payload_template"])
        if "surfaces_mode" in overrides:
            if overrides["surfaces_mode"] not in SURFACE_MODES:
                raise SpecError(f"surfaces_mode must be one of {SURFACE_MODES}")
            new.mode = overrides["surfaces_mode"]
        return new

    def to_legacy_dict(self) -> dict[str, Any]:
        """The ``{"attack": {...}, "packages": {...}}`` shape older code paths still consume."""
        d = copy.deepcopy(self.raw) if self.raw else {"attack": {}}
        a = d.setdefault("attack", {})
        a["id"], a["name"] = self.id, self.name
        a["surfaces"] = {"primary": [s.value for s in self.primary], "fallback": [s.value for s in self.fallback],
                         "mode": self.mode}
        a.setdefault("payload", {})["template"] = self.payload_template
        t = a.setdefault("target", {})
        t["inject_position"], t["inject_prefix"] = self.inject_position, self.inject_prefix
        return d


# --------------------------------------------------------------------------- tasks
@dataclass
class TaskSurfaces:
    """Ordered ``surface -> file patterns`` declared by a task's benign overlay."""
    task_id: str
    surfaces: dict[InjectionSurface, list[str]]
    description: str = ""
    source: Path | None = None

    @classmethod
    def load(cls, task_id: str | int, *, strict: bool = True) -> "TaskSurfaces":
        p = paths.task_overlay_path(task_id)
        return cls.from_dict(_read_toml(p), task_id=paths._norm("task", task_id), source=p, strict=strict)

    @classmethod
    def from_dict(cls, d: dict[str, Any], *, task_id: str, source: Path | None = None,
                  strict: bool = True) -> "TaskSurfaces":
        where = str(source or "<dict>")
        out: dict[InjectionSurface, list[str]] = {}
        for key, sdef in (d.get("surfaces", {}) or {}).items():
            if not isinstance(sdef, dict):
                continue
            name = str(sdef.get("type", key))
            try:
                s = parse_injection_surface(name, where=f"{where} [surfaces.{key}]")
            except SurfaceError:
                if strict:
                    raise
                continue
            if strict and "objects" in sdef:
                raise SpecError(f"{where} [surfaces.{key}]: legacy key `objects`; use `files`")
            files = [str(x) for x in (sdef.get("files", []) or [])]
            if strict and not files:
                raise SpecError(f"{where} [surfaces.{key}]: no files declared")
            out.setdefault(s, []).extend(f for f in files if f not in out.get(s, []))
        return cls(task_id=task_id, surfaces=out,
                   description=str((d.get("overlay", {}) or {}).get("description", "")), source=source)

    @property
    def declared(self) -> list[InjectionSurface]:
        return list(self.surfaces)


__all__ = ["AttackSpec", "TaskSurfaces", "SpecError"]
