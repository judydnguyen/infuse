"""``infuse`` — the single command-line entry point.

    infuse run      --task 1 --attack 1 --model gpt-4o-mini            one cell
    infuse batch    --attacks 1-10 --tasks 1-5 --models gpt-4o-mini    a grid (resumable)
    infuse batch    --experiment defense_grid --dry-run                 a saved grid
    infuse judge    [--trajectories-dir DIR]                            LLM judge over trajectories
    infuse records  [--results-dir DIR]                                 aggregate trajectories + judge → CSV
    infuse figures  [--out-dir figs]                                    paper figures from the CSV
    infuse attacks  list | compat                                       inspect the benchmark
    infuse tasks    list
    infuse serve-vllm llama_3_1_8b                                      local open-weight server
    infuse migrate-configs [--write]                                    normalise configs/overlays
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

os.environ.setdefault("MSWEA_SILENT_STARTUP", "1")

from infuse import __version__, paths  # noqa: E402
from infuse.surfaces import INJECT_POSITIONS, RESOLUTION_STRATEGIES  # noqa: E402

VARIANTS = ("default", "gcg", "troubleshoot")


def _ids(text: str | None) -> list[str]:
    from infuse.runners.batch import parse_id_list
    return parse_id_list(text)


def _csv(text: str | None) -> list[str]:
    return [x.strip() for x in text.split(",") if x.strip()] if text else []


# ----------------------------------------------------------------------------- run
def cmd_run(a: argparse.Namespace) -> int:
    from infuse.runners.run_test_task import run_test_task
    overrides = dict(a.attack_overrides or {})
    if a.inject_prefix is not None:
        overrides["inject_prefix"] = a.inject_prefix
    if a.inject_position:
        overrides["inject_position"] = a.inject_position
    if a.task_prefix and "inject_prefix" not in overrides:
        from infuse.runners.batch import _task_prefix_for
        p = _task_prefix_for(a.task)
        if p:
            overrides["inject_prefix"] = p
    if a.multi_surface:
        overrides["surfaces_mode"] = "multi"
    result = run_test_task(
        task_id=paths._norm("task", a.task), attack_id=a.attack, model_name=a.model, model_class=a.model_class,
        output_dir=str(paths.results_dir(a.results_dir)), use_docker=not a.no_docker, timeout_seconds=a.timeout,
        cost_limit=a.cost_limit, attack_overrides=overrides or None, defense_name=a.defense,
        defense_model=a.defense_model, overwrite=a.overwrite, obs_level=a.obs_level,
        resolution_strategy=a.strategy,
    )
    print(json.dumps(result, indent=2, default=str))
    return 0 if result.get("status") == "completed" else 1


def _add_run_like_args(p: argparse.ArgumentParser) -> None:
    from infuse.registry import DEFENSE_NAMES
    p.add_argument("--model-class", help="anthropic | litellm | vllm | ... (default: from models.yaml / auto)")
    p.add_argument("--defense", default="none", choices=DEFENSE_NAMES, metavar="NAME",
                   help=f"one of: {', '.join(DEFENSE_NAMES)}")
    p.add_argument("--defense-model", help="LLM used by input_filter/input_transform/output_filter/progent/camel")
    p.add_argument("--obs-level", default="default", choices=VARIANTS, help="payload variant")
    p.add_argument("--strategy", default="task_order", choices=RESOLUTION_STRATEGIES,
                   help="injection-target resolution strategy (task_order reproduces past runs)")
    p.add_argument("--task-prefix", action=argparse.BooleanOptionalAction, default=True,
                   help="prefix the payload with the task's entry in configs/task_inject_prefixes.json "
                        "(default on; tasks without an entry fall back to the attack's own inject_prefix). "
                        "--no-task-prefix disables it")
    p.add_argument("--inject-prefix", help="explicit payload prefix (overrides the task prefix)")
    p.add_argument("--inject-position", choices=INJECT_POSITIONS)
    p.add_argument("--attack-overrides", type=json.loads, metavar="JSON", help='e.g. \'{"surfaces_mode": "multi"}\'')
    p.add_argument("--cost-limit", type=float, help="USD cap per run (default: models.yaml or 0.005)")
    p.add_argument("--timeout", type=int, help="seconds")
    p.add_argument("--results-dir", help="absolute, or relative to DATA_ROOT_PATH")
    p.add_argument("--no-docker", action="store_true")
    p.add_argument("--overwrite", action="store_true", help="re-run even if a trajectory exists")


# ----------------------------------------------------------------------------- batch
def cmd_batch(a: argparse.Namespace) -> int:
    from infuse.runners.batch import BatchSpec, run_batch
    cli = dict(
        attacks=_ids(a.attacks), tasks=_ids(a.tasks), models=_csv(a.models), defenses=_csv(a.defenses),
        defense_model=a.defense_model, model_class=a.model_class, obs_level=a.obs_level if a.obs_level != "default" else None,
        task_prefix=a.task_prefix, inject_prefix=a.inject_prefix, inject_position=a.inject_position,
        attack_overrides=a.attack_overrides or {}, cost_limit=a.cost_limit, timeout=a.timeout,
        results_dir=a.results_dir, resolution_strategy=a.strategy if a.strategy != "task_order" else None,
        use_docker=None if not a.no_docker else False, overwrite=a.overwrite or None, jobs=a.jobs if a.jobs != 1 else None,
    )
    if a.multi_surface:
        cli["attack_overrides"] = {**cli["attack_overrides"], "surfaces_mode": "multi"}
    if a.experiment:
        spec = BatchSpec.from_experiment(a.experiment, **cli)
        if a.no_docker:
            spec.use_docker = False
    else:
        if not (cli["tasks"] and cli["models"]):
            print("batch: --tasks and --models are required (or --experiment NAME)", file=sys.stderr)
            return 2
        cli["use_docker"] = not a.no_docker
        spec = BatchSpec(**{k: v for k, v in cli.items() if v is not None}, name="adhoc")
        if not spec.defenses:
            spec.defenses = ["none"]
    summary = run_batch(spec, dry_run=a.dry_run)
    if a.summary:
        Path(a.summary).write_text(json.dumps(summary, indent=2, default=str))
    bad = sum(v for k, v in summary.get("status_counts", {}).items() if k != "completed")
    return 0 if bad == 0 else 1


# ----------------------------------------------------------------------------- judge / records / figures
def cmd_judge(a: argparse.Namespace) -> int:
    from infuse.judge import batch_llm_judge
    argv = ["--trajectories-dir", str(a.trajectories_dir or (paths.results_dir(a.results_dir) / "attack_task")),
            "--judge-model", a.judge_model]
    if a.skip_existing:
        argv.append("--skip-existing")
    for flag in ("attack_id", "benign_task_id", "model", "output_summary"):
        v = getattr(a, flag)
        if v:
            argv += [f"--{flag.replace('_', '-')}", str(v)]
    sys.argv = ["infuse judge"] + argv
    return batch_llm_judge.main() or 0


def cmd_records(a: argparse.Namespace) -> int:
    from infuse.analysis import records
    return records.main(a) or 0


def cmd_figures(a: argparse.Namespace) -> int:
    from infuse.analysis import figures
    return figures.main(a) or 0


# ----------------------------------------------------------------------------- introspection
def _attack_ids() -> list[str]:
    return sorted((p.name.split("_", 1)[1] for p in paths.ATTACKS_DIR.glob("attack_*")), key=int)


def _task_ids() -> list[str]:
    return sorted((p.name.split("_", 1)[1] for p in paths.TASKS_DIR.glob("task_*")), key=int)


def cmd_attacks_list(a: argparse.Namespace) -> int:
    from infuse.injection import AttackSpec
    rows = []
    for aid in _attack_ids():
        s = AttackSpec.load(aid, strict=not a.lenient)
        rows.append((s.id, s.name, ",".join(x.value for x in s.primary), ",".join(x.value for x in s.fallback),
                     s.inject_position, s.metadata.get("attack_category", "")))
    if a.json:
        print(json.dumps([dict(zip(("id", "name", "primary", "fallback", "position", "category"), r)) for r in rows], indent=2))
        return 0
    print(f"{'id':>4}  {'name':<48} {'primary':<44} {'fallback':<28} pos")
    for r in rows:
        print(f"{r[0]:>4}  {r[1][:48]:<48} {r[2]:<44} {r[3]:<28} {r[4]}")
    return 0


def cmd_tasks_list(a: argparse.Namespace) -> int:
    from infuse.injection import TaskSurfaces
    print(f"{'task':>6}  surfaces")
    for tid in _task_ids():
        ts = TaskSurfaces.load(tid, strict=not a.lenient)
        print(f"{tid:>6}  " + "  ".join(f"{s.value}={len(f)}" for s, f in ts.surfaces.items()))
    return 0


def compat_matrix(strategy: str = "task_order") -> dict[str, dict[str, list[str]]]:
    """``{attack: {task: [surface, ...]}}`` — surfaces whose files actually resolve, in selection order."""
    from infuse.injection import AttackSpec, TaskSurfaces, resolve
    tasks = {tid: TaskSurfaces.load(tid, strict=False) for tid in _task_ids()}
    out: dict[str, dict[str, list[str]]] = {}
    for aid in _attack_ids():
        spec = AttackSpec.load(aid, strict=False)
        row: dict[str, list[str]] = {}
        for tid, ts in tasks.items():
            workdir = paths.task_dir(tid) / "environment" / "app"
            seen: list[str] = []
            for c in resolve(spec, ts, workdir, strategy):
                if c.surface.value not in seen:
                    seen.append(c.surface.value)
            row[tid] = seen
        out[aid] = row
    return out


def cmd_attacks_compat(a: argparse.Namespace) -> int:
    m = compat_matrix(a.strategy)
    tasks = _task_ids()
    if a.json:
        print(json.dumps(m, indent=1))
        return 0
    missing = [(x, t) for x, row in m.items() for t, surf in row.items() if not surf]
    print(f"attack × task resolution ({a.strategy}): {len(m)} attacks × {len(tasks)} tasks, "
          f"{len(missing)} pair(s) with no injection target")
    abbrev = {"FILE_CONTENT": "F", "CONFIG_FILE": "C", "FILENAME": "N", "ARCHIVE_CONTENT": "A"}
    print("      " + " ".join(f"{t:>3}" for t in tasks))
    for x, row in m.items():
        print(f"{x:>5} " + " ".join(f"{(abbrev[row[t][0]] if row[t] else '.'):>3}" for t in tasks))
    print("legend: first surface that would be injected  F=FILE_CONTENT C=CONFIG_FILE N=FILENAME A=ARCHIVE_CONTENT  .=none")
    if missing and a.strict:
        return 1
    return 0


def cmd_migrate(a: argparse.Namespace) -> int:
    from infuse.injection.migrate import run
    run(write=a.write)
    return 0


def cmd_serve_vllm(a: argparse.Namespace) -> int:
    from infuse.runners.vllm_server import serve
    return serve(a.model_key, a.port, dry_run=a.dry_run)


# ----------------------------------------------------------------------------- parser
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="infuse", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--version", action="version", version=f"infuse {__version__}")
    sub = p.add_subparsers(dest="cmd", required=True)

    r = sub.add_parser("run", help="run one task, optionally under one attack")
    r.add_argument("--task", required=True, help="task id, e.g. 1 or task_1")
    r.add_argument("--attack", help="attack id, e.g. 1 or 101 (omit for benign)")
    r.add_argument("--model", default="gpt-4o-mini")
    r.add_argument("--multi-surface", action="store_true", help="inject into up to 3 surfaces")
    _add_run_like_args(r)
    r.set_defaults(fn=cmd_run)

    b = sub.add_parser("batch", help="run a grid; skips cells that already have a trajectory")
    b.add_argument("--experiment", help="name in benchmark/experiments/ or a YAML path; CLI flags override it")
    b.add_argument("--attacks", help='e.g. "1-36,101-120"; omit/empty for benign runs')
    b.add_argument("--tasks", help='e.g. "1-40" or "9,13,17"')
    b.add_argument("--models", help="comma-separated")
    b.add_argument("--defenses", help="comma-separated (default none)")
    b.add_argument("--multi-surface", action="store_true")
    b.add_argument("--jobs", type=int, default=1, help="parallel cells (Docker builds are heavy; 1-4)")
    b.add_argument("--dry-run", action="store_true", help="list cells without running")
    b.add_argument("--summary", help="write batch summary JSON here")
    _add_run_like_args(b)
    b.set_defaults(fn=cmd_batch)

    j = sub.add_parser("judge", help="LLM-judge collected trajectories (ASR + task completion)")
    j.add_argument("--trajectories-dir")
    j.add_argument("--results-dir", help="base results dir (default DATA_ROOT_PATH); judge reads <base>/attack_task")
    j.add_argument("--judge-model", default="gpt-4o-mini")
    j.add_argument("--skip-existing", action="store_true")
    j.add_argument("--attack-id"); j.add_argument("--benign-task-id"); j.add_argument("--model")
    j.add_argument("--output-summary")
    j.set_defaults(fn=cmd_judge)

    rc = sub.add_parser("records", help="aggregate trajectories + judge outputs into traj_records.csv")
    rc.add_argument("--results-dir", help="base results dir (default DATA_ROOT_PATH)")
    rc.add_argument("--benign", action="store_true", help="aggregate benign runs instead")
    rc.add_argument("--workers", type=int)
    rc.add_argument("--no-cache", action="store_true")
    rc.set_defaults(fn=cmd_records)

    f = sub.add_parser("figures", help="regenerate figures from the records CSVs")
    f.add_argument("--results-dir")
    f.add_argument("--out-dir", default="figs")
    f.add_argument("--which", default="all", help="comma list of figure names, or all")
    f.set_defaults(fn=cmd_figures)

    at = sub.add_parser("attacks", help="inspect attacks")
    ats = at.add_subparsers(dest="sub", required=True)
    al = ats.add_parser("list"); al.add_argument("--json", action="store_true"); al.add_argument("--lenient", action="store_true")
    al.set_defaults(fn=cmd_attacks_list)
    ac = ats.add_parser("compat", help="which surface each attack × task pair would inject into")
    ac.add_argument("--strategy", default="task_order", choices=RESOLUTION_STRATEGIES)
    ac.add_argument("--json", action="store_true"); ac.add_argument("--strict", action="store_true", help="exit 1 if any pair has no target")
    ac.set_defaults(fn=cmd_attacks_compat)

    tk = sub.add_parser("tasks", help="inspect tasks")
    tks = tk.add_subparsers(dest="sub", required=True)
    tl = tks.add_parser("list"); tl.add_argument("--lenient", action="store_true"); tl.set_defaults(fn=cmd_tasks_list)

    mg = sub.add_parser("migrate-configs", help="normalise attack configs and task overlays (dry-run unless --write)")
    mg.add_argument("--write", action="store_true"); mg.set_defaults(fn=cmd_migrate)

    sv = sub.add_parser("serve-vllm", help="start a vLLM server for a models.yaml key")
    sv.add_argument("model_key"); sv.add_argument("--port", type=int); sv.add_argument("--dry-run", action="store_true")
    sv.set_defaults(fn=cmd_serve_vllm)
    return p


def _logs_to_stderr() -> None:
    """stdout is reserved for machine-readable output (JSON); every log line goes to stderr."""
    import logging
    os.environ.setdefault("LITELLM_LOG", "WARNING")
    logging.basicConfig(level=logging.INFO, stream=sys.stderr, format="%(levelname)s - %(name)s - %(message)s")
    try:
        import litellm
        litellm.suppress_debug_info = True
        litellm.set_verbose = False
    except Exception:
        pass
    for name in ("LiteLLM", "LiteLLM Router", "LiteLLM Proxy", "httpx"):
        lg = logging.getLogger(name)
        lg.handlers = [logging.StreamHandler(sys.stderr)]
        lg.propagate = False
        lg.setLevel(logging.WARNING)


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    _logs_to_stderr()
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
