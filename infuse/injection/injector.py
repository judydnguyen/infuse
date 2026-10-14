"""Build-time injection: resolve → select → handle, and record every decision."""
from __future__ import annotations

import logging
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from infuse.injection.assemble import assemble_payload, payload_sha256
from infuse.injection.handlers import handler_for
from infuse.injection.resolver import Candidate, resolve, select
from infuse.injection.spec import AttackSpec, TaskSurfaces

logger = logging.getLogger(__name__)


@dataclass
class InjectionRecord:
    """What was injected, where, and why. Serialised into the run manifest."""
    attack_id: str
    task_id: str
    strategy: str
    mode: str
    variant: str
    position: str
    prefix: str
    payload: str
    payload_sha256: str
    candidates: list[dict[str, str]] = field(default_factory=list)   # [{surface, path}]
    selected: list[dict[str, str]] = field(default_factory=list)     # [{surface, target, written}]
    written_files: list[str] = field(default_factory=list)           # workdir-relative

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def inject(spec: AttackSpec, task: TaskSurfaces, workdir: Path, *, strategy: str = "task_order",
           variant: str = "default", payload: str | None = None) -> InjectionRecord:
    """Inject *spec*'s payload into the materialised *workdir* of *task*.

    *payload* may be passed pre-assembled (the runner does this so the same
    string is also handed to ``setup.sh``); otherwise it is assembled here.
    """
    workdir = Path(workdir)
    payload = assemble_payload(spec, variant) if payload is None else payload
    candidates = resolve(spec, task, workdir, strategy)
    chosen = select(candidates, spec.mode)
    rec = InjectionRecord(
        attack_id=spec.id, task_id=task.task_id, strategy=strategy, mode=spec.mode, variant=variant,
        position=spec.inject_position, prefix=spec.inject_prefix, payload=payload,
        payload_sha256=payload_sha256(payload),
        candidates=[{"surface": c.surface.value, "path": c.rel(workdir)} for c in candidates],
    )
    if not chosen:
        logger.warning("attack %s / %s: no injection target (task declares %s, attack supports %s)",
                       spec.id, task.task_id, [s.value for s in task.declared], [s.value for s in spec.supported])
        return rec
    for c in chosen:
        res = handler_for(c.surface, c.path)(c.path, payload, spec.inject_position, workdir)
        rel_written = _rel(res.written, workdir)
        rec.selected.append({"surface": c.surface.value, "target": c.rel(workdir), "written": rel_written})
        rec.written_files.append(rel_written)
        logger.info("attack %s → %s [%s]", spec.id, rel_written, c.surface.value)
    return rec


def plan(spec: AttackSpec, task: TaskSurfaces, workdir: Path, *, strategy: str = "task_order") -> list[Candidate]:
    """Dry run: what :func:`inject` would choose, without touching files."""
    return select(resolve(spec, task, workdir, strategy), spec.mode)


def _rel(p: Path, root: Path) -> str:
    try:
        return str(p.relative_to(root))
    except ValueError:
        return str(p)


__all__ = ["InjectionRecord", "inject", "plan"]
