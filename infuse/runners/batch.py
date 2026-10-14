"""Grid runner: attacks × tasks × models × defenses, resumable, dry-runnable.

Replaces the 13 ``batch_collect_*.sh`` / ``ablations/*.sh`` scripts. Each cell
is one call to :func:`infuse.runners.run_test_task.run_test_task`; results land in
the legacy layout under ``paths.results_dir(results_dir)`` and a per-batch log
is written to ``<results>/batch_logs/``.
"""
from __future__ import annotations

import datetime as _dt
import itertools
import json
import logging
import sys
import time
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterable

import yaml

from infuse import paths
from infuse.registry import default_cost_limit, needs_model

logger = logging.getLogger(__name__)


@dataclass
class Cell:
    attack: str | None   # None = benign
    task: str
    model: str
    defense: str = "none"

    @property
    def attack_label(self) -> str:
        return self.attack if self.attack else "benign"

    def output_root(self, base: Path) -> Path:
        if self.attack is None:
            return paths.benign_results_dir(self.model, self.task, base)
        return paths.attack_results_dir(self.attack, self.task, self.model, base)


@dataclass
class BatchSpec:
    attacks: list[str]            # [] => benign runs
    tasks: list[str]
    models: list[str]
    defenses: list[str] = field(default_factory=lambda: ["none"])
    defense_model: str | None = None
    model_class: str | None = None
    obs_level: str = "default"
    task_prefix: bool = True   # per-task prefix table; --no-task-prefix turns it off
    inject_prefix: str | None = None
    inject_position: str | None = None
    attack_overrides: dict[str, Any] = field(default_factory=dict)
    cost_limit: float | None = None
    timeout: int | None = None
    results_dir: str | None = None
    resolution_strategy: str = "task_order"
    use_docker: bool = True
    overwrite: bool = False
    jobs: int = 1
    name: str | None = None

    @classmethod
    def from_experiment(cls, name_or_path: str, **cli_overrides: Any) -> "BatchSpec":
        p = Path(name_or_path)
        if not p.exists():
            p = paths.EXPERIMENTS_DIR / f"{name_or_path}.yaml"
        if not p.exists():
            raise FileNotFoundError(f"experiment not found: {name_or_path} (looked in {paths.EXPERIMENTS_DIR})")
        data = yaml.safe_load(p.read_text()) or {}
        data.setdefault("name", p.stem)
        for k, v in cli_overrides.items():
            if v is None or v == [] or v == {}:
                continue  # unset on the CLI: keep the YAML value
            data[k] = v
        data["attacks"] = [str(a) for a in _expand_ids(data.get("attacks", []))]
        data["tasks"] = [str(t) for t in _expand_ids(data.get("tasks", []))]
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})

    def cells(self) -> list[Cell]:
        attacks: list[str | None] = list(self.attacks) or [None]
        return [Cell(a, t, m, d) for a, t, m, d in itertools.product(attacks, self.tasks, self.models, self.defenses)]


def _expand_ids(values: Iterable[Any]) -> list[str]:
    """Accept ``[1, 2, "5-8", "101,102"]`` style lists."""
    out: list[str] = []
    for v in values:
        for part in str(v).split(","):
            part = part.strip()
            if not part:
                continue
            if "-" in part and all(x.strip().isdigit() for x in part.split("-", 1)):
                lo, hi = (int(x) for x in part.split("-", 1))
                out += [str(i) for i in range(lo, hi + 1)]
            else:
                out.append(part)
    return out


def parse_id_list(text: str | None) -> list[str]:
    return _expand_ids([text]) if text else []


def _existing_trajectory(cell: Cell, base: Path) -> Path | None:
    root = cell.output_root(base)
    if not root.exists():
        return None
    hits = sorted(root.glob("*.traj.json"))
    return hits[0] if hits else None


def _task_prefix_for(task: str) -> str | None:
    try:
        table = json.loads(paths.TASK_PREFIX_JSON.read_text())
    except FileNotFoundError:
        return None
    return table.get(str(paths._id(task))) or None


def build_overrides(spec: BatchSpec, task: str) -> dict[str, Any]:
    ov = dict(spec.attack_overrides)
    prefix = spec.inject_prefix
    if prefix is None and spec.task_prefix:
        prefix = _task_prefix_for(task)
    if prefix:
        ov["inject_prefix"] = prefix
    if spec.inject_position:
        ov["inject_position"] = spec.inject_position
    return ov


def run_cell(cell: Cell, spec: BatchSpec, base: Path) -> dict[str, Any]:
    from infuse.runners.run_test_task import run_test_task
    t0 = time.time()
    try:
        result = run_test_task(
            task_id=paths._norm("task", cell.task),
            attack_id=cell.attack,
            model_name=cell.model,
            model_class=spec.model_class,
            output_dir=str(base),
            use_docker=spec.use_docker,
            timeout_seconds=spec.timeout,
            cost_limit=spec.cost_limit if spec.cost_limit is not None else default_cost_limit(cell.model),
            attack_overrides=build_overrides(spec, cell.task) if cell.attack else None,
            defense_name=cell.defense,
            defense_model=spec.defense_model,
            overwrite=spec.overwrite,
            obs_level=spec.obs_level,
            resolution_strategy=spec.resolution_strategy,
            run_metadata={"batch": spec.name, "defense_model": spec.defense_model},
        )
        status = result.get("status", "unknown")
        return {"cell": asdict(cell), "status": status, "cost": result.get("cost"), "seconds": round(time.time() - t0, 1),
                "output_file": result.get("output_file"), "error": result.get("error")}
    except Exception as e:  # keep the grid going
        return {"cell": asdict(cell), "status": "exception", "seconds": round(time.time() - t0, 1),
                "error": f"{type(e).__name__}: {e}", "traceback": traceback.format_exc()}


def run_batch(spec: BatchSpec, *, dry_run: bool = False, stream=None) -> dict[str, Any]:
    stream = stream or sys.stderr
    base = paths.results_dir(spec.results_dir)
    cells = spec.cells()
    for d in spec.defenses:
        if needs_model(d) and not spec.defense_model:
            raise ValueError(f"defense {d!r} needs --defense-model")
    todo, skipped = [], []
    for c in cells:
        if not spec.overwrite and _existing_trajectory(c, base):
            skipped.append(c)
        else:
            todo.append(c)
    summary: dict[str, Any] = {
        "name": spec.name, "results_dir": str(base), "cells_total": len(cells), "cells_skipped": len(skipped),
        "cells_to_run": len(todo), "started": _dt.datetime.now().isoformat(timespec="seconds"), "results": [],
    }
    print(f"[batch] {len(cells)} cells, {len(skipped)} already done, {len(todo)} to run → {base}", file=stream)
    if dry_run:
        for c in todo:
            print(f"  run   attack={c.attack_label:<7} task={c.task:<4} model={c.model:<40} defense={c.defense}", file=stream)
        for c in skipped:
            print(f"  skip  attack={c.attack_label:<7} task={c.task:<4} model={c.model:<40} defense={c.defense}", file=stream)
        return summary

    log_dir = base / "batch_logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / f"batch_{_dt.datetime.now():%Y%m%d_%H%M%S}.jsonl"
    with open(log_path, "a") as log:
        def _record(res: dict[str, Any]) -> None:
            summary["results"].append(res)
            log.write(json.dumps(res, default=str) + "\n")
            log.flush()
            c = res["cell"]
            print(f"[batch] {res['status']:<10} attack={c['attack'] or 'benign':<7} task={c['task']:<4} "
                  f"model={c['model']:<40} defense={c['defense']:<24} {res['seconds']}s", file=stream)

        if spec.jobs <= 1:
            for c in todo:
                _record(run_cell(c, spec, base))
        else:
            with ThreadPoolExecutor(max_workers=spec.jobs) as pool:
                futs = {pool.submit(run_cell, c, spec, base): c for c in todo}
                for f in as_completed(futs):
                    _record(f.result())
    summary["finished"] = _dt.datetime.now().isoformat(timespec="seconds")
    summary["log"] = str(log_path)
    counts: dict[str, int] = {}
    for r in summary["results"]:
        counts[r["status"]] = counts.get(r["status"], 0) + 1
    summary["status_counts"] = counts
    print(f"[batch] done: {counts}  log={log_path}", file=stream)
    return summary


__all__ = ["BatchSpec", "Cell", "run_batch", "run_cell", "parse_id_list", "build_overrides"]
