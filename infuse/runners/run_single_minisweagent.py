"""
Run Single Test with MiniSWE Agent

Executes a single agent test using the minisweagent framework with Task and Attack support.
"""

import argparse
import copy
import json
import os
import subprocess
import sys
import traceback
import uuid
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple


from infuse.runners.task_runner import run_task
from infuse.runners.common import load_default_config, normalize_model_name
from infuse.runners.attack_utils import create_attack_from_config
from infuse.tasks.task_suite import Task, get_task_by_id, SurfaceType, ExecutionTrace
from infuse.attacks.base_attack import Attack

from infuse.paths import TASKS_DIR, ATTACKS_DIR, TEMPLATES_DIR
_DATA_DIR = TEMPLATES_DIR

# ---------------------------------------------------------------------------
# Attack config overrides
# ---------------------------------------------------------------------------

_OVERRIDE_SCHEMA: Dict[str, Dict[str, Any]] = {
    "inject_position": {
        "path": ["attack", "target", "inject_position"],
        "allowed": {"prepend", "append", "inline", "replace"},
    },
    "inject_prefix": {
        "path": ["attack", "target", "inject_prefix"],
        "allowed": None,  # any string
    },
    "payload_template": {
        "path": ["attack", "payload", "template"],
        "allowed": None,
    },
    "surfaces_mode": {
        "path": ["attack", "surfaces", "mode"],
        "allowed": {"single", "multi"},
    },
}


def _apply_attack_overrides(
    attack_config: Dict[str, Any],
    overrides: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Return a deep copy of *attack_config* with *overrides* applied.

    *overrides* is a flat dict whose keys must be in ``_OVERRIDE_SCHEMA``.
    Pass ``None`` (the default) to return the config unchanged.

    Example::

        overrides = {"inject_position": "prepend", "inject_prefix": "IGNORE PRIOR INSTRUCTIONS"}
    """
    if not overrides:
        return attack_config

    unknown = set(overrides) - set(_OVERRIDE_SCHEMA)
    if unknown:
        raise ValueError(
            f"Unknown attack override keys: {sorted(unknown)}. "
            f"Allowed: {sorted(_OVERRIDE_SCHEMA)}"
        )

    config = copy.deepcopy(attack_config)
    for key, value in overrides.items():
        spec = _OVERRIDE_SCHEMA[key]
        if spec["allowed"] is not None and value not in spec["allowed"]:
            raise ValueError(
                f"Invalid value {value!r} for override key {key!r}. "
                f"Allowed values: {spec['allowed']}"
            )
        node = config
        for part in spec["path"][:-1]:
            node = node.setdefault(part, {})
        node[spec["path"][-1]] = value
        print(f"✓ Attack override applied: {key} = {value!r}", file=sys.stderr)

    return config


# ---------------------------------------------------------------------------
# Script helpers
# ---------------------------------------------------------------------------

def _run_script(
    script: Path,
    args: List[str],
    cwd: Path,
    timeout: int,
    label: str,
) -> bool:
    """Run a shell script and return True on success."""
    cmd = ["bash", str(script.resolve())] + args
    print(f"✓ Running {label}: {' '.join(cmd)}", file=sys.stderr)
    try:
        result = subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True, timeout=timeout)
        if result.returncode != 0:
            print(f"⚠ {label} failed (code {result.returncode})", file=sys.stderr)
            if result.stdout:
                print(f"  stdout: {result.stdout}", file=sys.stderr)
            if result.stderr:
                print(f"  stderr: {result.stderr}", file=sys.stderr)
            return False
        print(f"  {label} completed successfully", file=sys.stderr)
        if result.stdout:
            print(f"  {result.stdout.strip()}", file=sys.stderr)
        return True
    except subprocess.TimeoutExpired:
        print(f"⚠ {label} timed out after {timeout}s", file=sys.stderr)
        return False
    except Exception as e:
        print(f"⚠ {label} error: {e}", file=sys.stderr)
        return False


def run_setup_script(task_dir: Path, task_id: str, attack_payload: Optional[str] = None) -> bool:
    """
    Run setup.sh if it exists in the task environment directory.

    For attack runs, writes *attack_payload* to ``attack_payload.md`` and passes
    its path to ``setup.sh``.  For benign runs, uses ``setup_args`` from
    ``task.toml``.  Returns True if the script succeeded or doesn't exist.
    """
    try:
        import tomllib as tomli
    except ImportError:
        import tomli  # type: ignore

    env_dir = task_dir / task_id / "environment"
    setup_script = env_dir / "setup.sh"

    if not setup_script.exists():
        return True

    attack_payload_file = None
    try:
        if attack_payload:
            attack_payload_file = env_dir / "attack_payload.md"
            try:
                attack_payload_file.write_text(attack_payload)
                print(f"Attack payload: {attack_payload!r}", file=sys.stderr)
                print(f"✓ Wrote attack payload to: {attack_payload_file}", file=sys.stderr)
            except Exception as e:
                print(f"⚠ Failed to write attack payload: {e}", file=sys.stderr)
                return False
            script_args = [str(attack_payload_file.resolve())]
        else:
            task_toml = task_dir / task_id / "task.toml"
            setup_args: List[str] = []
            if task_toml.exists():
                with open(task_toml, "rb") as f:
                    task_config = tomli.load(f)
                raw = task_config.get("environment", {}).get("setup_args", [])
                setup_args = [raw] if isinstance(raw, str) else [str(a) for a in raw]

            if not setup_args:
                print(f"  setup.sh present for {task_id} but no setup_args in task.toml; skipping", file=sys.stderr)
                return True
            script_args = setup_args

        return _run_script(setup_script, script_args, env_dir, timeout=300, label="setup script")
    finally:
        if attack_payload_file and attack_payload_file.exists():
            try:
                attack_payload_file.unlink()
            except Exception:
                pass


def run_cleanup_script(task_dir: Path, task_id: str) -> None:
    """Run clean.sh if it exists in the task environment directory."""
    env_dir = task_dir / task_id / "environment"
    cleanup_script = env_dir / "clean.sh"
    if cleanup_script.exists():
        _run_script(cleanup_script, [], env_dir, timeout=120, label="cleanup script")


# ---------------------------------------------------------------------------
# Attack template helpers
# ---------------------------------------------------------------------------

def _build_attack_payload(attack_config: Dict[str, Any], obs_level: str) -> str:
    """Assemble the payload string (kept as a thin alias; see :mod:`infuse.injection.assemble`)."""
    from infuse.injection import AttackSpec, assemble_payload
    return assemble_payload(AttackSpec.from_dict(attack_config, strict=False), obs_level)


# ---------------------------------------------------------------------------
# Main runner
# ---------------------------------------------------------------------------

def run_single_test_with_minisweagent(
    task_id: Optional[str] = None,
    task: Optional[Task] = None,
    attack: Optional[Attack] = None,
    attack_config: Optional[Dict[str, Any]] = None,
    model_name: Optional[str] = None,
    model_config: Optional[Dict] = None,
    env_config: Optional[Dict] = None,
    agent_config: Optional[Dict] = None,
    injection_path: Optional[str] = None,
    output_dir: Optional[str] = None,
    data_root: Optional[str] = None,
    work_root: Optional[str] = None,
    timeout_seconds: Optional[int] = None,
    cost_limit: Optional[float] = None,
    use_docker: bool = False,
    docker_image: str = "agent-bench-base:latest",
    use_daytona: bool = False,
    daytona_image: Optional[str] = None,
    trace: Optional[ExecutionTrace] = None,
    data_in_image: bool = False,
    task_dir: Optional[str] = None,
    overwrite: bool = False,
    obs_level: str = "default",
    attack_overrides: Optional[Dict[str, Any]] = None,
    defense_name: Optional[str] = None,
    resolution_strategy: str = "task_order",
    run_metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Run a single test using the minisweagent framework.

    ``resolution_strategy`` selects how injection targets are chosen (see
    :mod:`infuse.injection.resolver`); ``run_metadata`` is merged into the run manifest.

    Returns a dictionary with test results including the ExecutionTrace.
    """
    print("=" * 60, file=sys.stderr)
    print("INITIALIZING MINISWEAGENT", file=sys.stderr)
    print("=" * 60, file=sys.stderr)

    if use_docker and use_daytona:
        raise ValueError("Only one of use_docker/use_daytona can be enabled")

    materializer = None
    cleanup_needed = False
    injection_record = None
    verifier_baseline = None
    tasks_root_for_cleanup = None
    task_id_for_cleanup = None

    if task_dir is None:
        task_dir = str(TASKS_DIR)
        
    attack_id = None
    if attack:
        attack_id = attack.attack_id
    elif attack_config:
        attack_id = attack_config.get("attack", attack_config).get("id", "unknown")

    if attack_config and attack_overrides:
        attack_config = _apply_attack_overrides(attack_config, attack_overrides)

    # ------------------------------------------------------------------
    # Load task
    # ------------------------------------------------------------------
    if task is None:
        if task_id is None:
            raise ValueError("Either task or task_id must be provided")

        if isinstance(task_id, str) and task_id.startswith("task_"):
            from infuse.envs.test_task_materializer import TestTaskMaterializer

            tasks_root = Path(task_dir)
            if not tasks_root.exists():
                raise ValueError(f"Tasks directory not found: {tasks_root}")

            materializer = TestTaskMaterializer(tasks_root)
            task_config = materializer.load_task_config(task_id)
            instruction = materializer.get_instruction(task_id)
            metadata = task_config.get("metadata", {})

            tasks_root_for_cleanup = tasks_root
            task_id_for_cleanup = task_id

            attack_payload_for_setup = _build_attack_payload(attack_config, obs_level) if attack_config else None

            if not run_setup_script(tasks_root, task_id, attack_payload_for_setup):
                raise RuntimeError(f"Setup script failed for task {task_id}")
            cleanup_needed = True

            class TestTask(Task):
                def __init__(self, task_id: str, instruction: str, task_config: Dict[str, Any]):
                    super().__init__(
                        task_id=task_id,
                        category=metadata.get("category", ""),
                        user_goal=instruction,
                        prompt_example=instruction,
                        script_test="",
                        groundtruth_goal="",
                        expected_surfaces=[],
                    )
                    self._instruction = instruction
                    self.task_config = task_config

                def get_prompt(self) -> str:
                    return self._instruction

                def setup(self, env):
                    pass  # Handled by the materializer

                def expected_surfaces_set(self):
                    overlay = materializer.load_benign_overlay(task_id)
                    surface_types = set()
                    for value in overlay.get("surfaces", {}).values():
                        if isinstance(value, dict) and "type" in value:
                            try:
                                surface_types.add(SurfaceType(value["type"]))
                            except (ValueError, AttributeError):
                                pass
                    return surface_types

                def success_criteria(self, trace):
                    return True  # Evaluated by test.sh

            task = TestTask(task_id, instruction, task_config)
            print(f"✓ Loaded task {task_id} from test_tasks: {task.category}", file=sys.stderr)
            print(f"  Goal: {task.user_goal[:80]}...", file=sys.stderr)

            if use_docker and materializer is not None:
                docker_image = task_config.get("environment", {}).get("docker_image", f"{task_id}:latest")
                print(f"Payload: {attack_payload_for_setup!r}", file=sys.stderr)
                docker_attack_config = attack_config
                if attack_config and attack_payload_for_setup is not None:
                    # The exact string handed to setup.sh is also what gets injected.
                    docker_attack_config = {**attack_config, "_assembled_payload": attack_payload_for_setup}
                try:
                    # Resolve attack directory if provided
                    attack_dir_abs = str(ATTACKS_DIR / f"attack_{attack_id}") if attack_config else None
                    print(f"attack_dir_abs: {attack_dir_abs}", file=sys.stderr)
                    materializer.build_docker_image(task_id, docker_image, docker_attack_config, attack_dir_abs=attack_dir_abs,
                                                    resolution_strategy=resolution_strategy, payload_variant=obs_level)
                    injection_record = materializer._last_injection_record
                    if attack_config:
                        from infuse.runners.verifier import baseline as _verifier_baseline
                        _inj_files = injection_record.written_files if injection_record else []
                        verifier_baseline = _verifier_baseline(docker_image, attack_id, injected_files=_inj_files)
                        if verifier_baseline.get("passed"):
                            print(f"⚠ verifier for attack {attack_id} already passes on the untouched image "
                                  f"(detects the planted payload, not agent behaviour)", file=sys.stderr)
                    if attack_config and materializer._last_attacked_files:
                        for f in materializer._last_attacked_files:
                            print(f"✓ Attack target: {f}", file=sys.stderr)
                    print(f"✓ Built Docker image: {docker_image}", file=sys.stderr)
                    data_in_image = True

                    if trace is None:
                        trace = ExecutionTrace(
                            task_id=task.task_id,
                            metadata={
                                "category": task.category,
                                "user_goal": task.user_goal,
                                "environment_files": [str(f) for f in materializer.get_environment_files(task_id)],
                            },
                        )
                        materializer.initialize_trace_with_environment(task_id, trace, attack_config)
                        print(f"✓ Initialized trace with {len(trace.events)} environment events", file=sys.stderr)
                except Exception as e:
                    print(f"⚠ Failed to build Docker image: {e}", file=sys.stderr)
                    if cleanup_needed and tasks_root_for_cleanup and task_id_for_cleanup:
                        run_cleanup_script(tasks_root_for_cleanup, task_id_for_cleanup)
                    raise
        else:
            # Legacy: load from BENIGN_TASKS.json (task IDs 1–26)
            try:
                task = get_task_by_id(int(task_id))
                print(f"✓ Loaded task {task_id} from BENIGN_TASKS.json (legacy): {task.category}", file=sys.stderr)
                print(f"  Goal: {task.user_goal[:80]}...", file=sys.stderr)
            except (ValueError, TypeError):
                raise ValueError(
                    f"Task ID must be an integer (1-26) for BENIGN_TASKS.json or start with 'task_' for test_tasks. "
                    f"Got: {task_id}."
                )

    # ------------------------------------------------------------------
    # Execution trace
    # ------------------------------------------------------------------
    if trace is None:
        trace = ExecutionTrace(
            task_id=task.task_id,
            metadata={"category": task.category, "user_goal": task.user_goal},
        )
    else:
        trace.metadata.update({"category": task.category, "user_goal": task.user_goal})
        init_events = [e for e in trace.events if e.step == 0]
        print(f"✓ Using pre-initialized trace with {len(trace.events)} events ({len(init_events)} at step 0)", file=sys.stderr)
        if init_events:
            print(f"  Initialization events: {[e.path for e in init_events[:3]]}", file=sys.stderr)

    # ------------------------------------------------------------------
    # Attack
    # ------------------------------------------------------------------

    # attack = create_attack_from_config()

    # if attack:
    #     print(f"✓ Attack: {attack.attack_id}", file=sys.stderr)
    #     print(f"  Surfaces: {[s.value for s in attack.target_surfaces]}", file=sys.stderr)

    # ------------------------------------------------------------------
    # Paths
    # ------------------------------------------------------------------
    data_root_path = Path(data_root).resolve() if data_root else None
    if data_root_path:
        print(f"✓ Data root: {data_root_path}", file=sys.stderr)

    if work_root and not use_docker and not use_daytona:
        work_root_path = Path(work_root)
        work_root_path.mkdir(parents=True, exist_ok=True)
        env_config = env_config or {}
        env_config["cwd"] = str(work_root_path)
        env_config.setdefault("env", {})["PWD"] = str(work_root_path)
        print(f"✓ Work root: {work_root_path}", file=sys.stderr)

    # ------------------------------------------------------------------
    # Model
    # ------------------------------------------------------------------
    model_config = model_config or {}
    model_name = model_name or model_config.get("model_name") or os.getenv("MSWEA_MODEL_NAME", "gpt-4")
    normalized = normalize_model_name(model_name, warn=False)
    if normalized != model_name:
        print(f"⚠ Normalized: {model_name} → {normalized}", file=sys.stderr)
    model_name = normalized
    model_config["model_name"] = model_name
    print(f"Model: {model_name}", file=sys.stderr)

    # ------------------------------------------------------------------
    # Agent config
    # ------------------------------------------------------------------
    default_agent_config = load_default_config().get("agent", {})
    agent_config = {**default_agent_config, **(agent_config or {})}
    if cost_limit is not None:
        agent_config["cost_limit"] = cost_limit
    if attack:
        agent_config["_attack"] = attack
        agent_config["_trace"] = trace
    if defense_name and defense_name.lower() not in ("none", ""):
        if "_defense" not in agent_config:
            from infuse.runners.run_test_task import _build_defense
            defense_model_name = os.environ.get("DEFENSE_MODEL") or None
            agent_config["_defense"] = _build_defense(defense_name, defense_model_name)
            print(
                f"✓ Defense: {defense_name}"
                + (f" (model: {defense_model_name})" if defense_model_name else ""),
                file=sys.stderr,
            )
        else:
            print(f"✓ Defense: {agent_config['_defense']}", file=sys.stderr)

    env_config = env_config or load_default_config().get("environment", {})

    # ------------------------------------------------------------------
    # Output path
    # ------------------------------------------------------------------
    output_dir = output_dir or "./results"
    run_id = str(uuid.uuid4())[:8]
    model_slug = model_name.replace("/", "_").replace(":", "_")
    is_attack_task = attack is not None or attack_config is not None

    # attack_id = None
    # if attack:
    #     attack_id = attack.attack_id
    # elif attack_config:
    #     attack_id = attack_config.get("attack", attack_config).get("id", "unknown")

    if is_attack_task:
        benign_id = task.task_id.replace("benign_", "").replace("task_", "")
        attack_dir = f"{attack_id}_{obs_level}" if obs_level != "default" else str(attack_id)
        output_path = Path(output_dir) / "attack_task" / attack_dir / benign_id / model_slug
        if defense_name and defense_name.lower() not in ("none", ""):
            output_path = output_path / defense_name
        suffix = f"_attack{attack_id}"
    else:
        output_path = Path(output_dir) / "benign_task" / model_slug / task.task_id
        if defense_name and defense_name.lower() not in ("none", ""):
            output_path = output_path / defense_name
        suffix = ""

    output_path.mkdir(parents=True, exist_ok=True)
    output_file = output_path / f"{task.task_id}_{run_id}{suffix}.traj.json"

    # ------------------------------------------------------------------
    # Docker / Daytona setup
    # ------------------------------------------------------------------
    docker_volumes: List[str] = []
    docker_run_args: Optional[List[str]] = None
    docker_cwd = "/work"
    daytona_cwd = work_root if work_root and use_daytona else "/work"
    daytona_sync_dirs: List[Tuple[str, str]] = []

    evals_dir = _DATA_DIR / "evals"

    if use_docker:
        if data_in_image:
            docker_cwd = "/app"
            docker_run_args = ["--rm", "--tmpfs", "/tmp:rw,noexec,nosuid,size=100m,mode=1777"]
            print(f"✓ Docker: data in image at /app", file=sys.stderr)
            agent_config.setdefault("workspace_dir", "/app")
        else:
            docker_cwd = work_root or "/work"
            docker_run_args = [
                "--rm",
                "--tmpfs", "/work:rw,noexec,nosuid,size=1g,mode=1777",
                "--tmpfs", "/tmp:rw,noexec,nosuid,size=100m,mode=1777",
                "--read-only",
            ]
            if docker_cwd == "/app":
                docker_cwd = "/work/app"
                print(f"✓ Docker: using /work/app as working directory", file=sys.stderr)
            print(f"✓ Docker: tmpfs, read-only rootfs, network enabled", file=sys.stderr)

            if data_root_path:
                if not data_root_path.exists():
                    raise ValueError(f"Data root does not exist: {data_root_path}")
                docker_volumes.append(f"{data_root_path}:/workspace/my_pc:ro")
                print(f"✓ Mount: {data_root_path} → /workspace/my_pc (ro)", file=sys.stderr)

            if evals_dir.exists():
                docker_volumes.append(f"{evals_dir.resolve()}:/app/data/evals:ro")
                print(f"✓ Mount: evals → /app/data/evals (ro)", file=sys.stderr)

            agent_config.setdefault("workspace_dir", docker_cwd if docker_cwd != "/work" else (work_root or "/work"))

    if use_daytona:
        if data_root_path:
            daytona_sync_dirs.append((str(data_root_path), "/workspace/my_pc"))
            print(f"✓ Daytona sync: {data_root_path} → /workspace/my_pc", file=sys.stderr)
        if evals_dir.exists():
            daytona_sync_dirs.append((str(evals_dir.resolve()), "/app/data/evals"))
            print(f"✓ Daytona sync: evals → /app/data/evals", file=sys.stderr)
        agent_config.setdefault("workspace_dir", work_root or "/work")

    print(f"\n{'=' * 60}", file=sys.stderr)
    print(f"TASK: {task.task_id}", file=sys.stderr)
    print(f"{'=' * 60}", file=sys.stderr)
    print(f"Description: {task.get_prompt()[:100]}...", file=sys.stderr)
    print(f"Expected surfaces: {[s.value for s in task.expected_surfaces_set()]}", file=sys.stderr)
    print(f"Output: {output_file}", file=sys.stderr)

    # attack_injection_config = None
    # if attack:
    #     attack_injection_config = {
    #         "inject_attack": True,
    #         "attack_id": attack.attack_id,
    #         "attack_surfaces": [s.value for s in attack.target_surfaces],
    #     }
    if attack_config:
        attack_injection_config = {
            "inject_attack": True,
            "attack_id": attack_config.get("attack", attack_config).get("id", "unknown"),
            "attack_surfaces": [s.value for s in create_attack_from_config(attack_config).target_surfaces],
            "injection": injection_record.to_dict() if injection_record else None,
            "verifier_baseline": verifier_baseline,
        }
    else:
        attack_injection_config = None

    task_type = "attack" if is_attack_task else "benign"

    # ------------------------------------------------------------------
    # Execute
    # ------------------------------------------------------------------
    try:
        if attack_injection_config:
            print(f"attack_injection_config: {attack_injection_config}", file=sys.stderr)
            print(f"attack: {attack}", file=sys.stderr)
        result = run_task(
            task_entry=task,
            task_type=task_type,
            model_name=model_name,
            model_config=model_config,
            env_config=env_config,
            agent_config=agent_config,
            output_path=output_file,
            attack_injection_config=attack_injection_config,
            attack=attack,
            trace=trace,
            timeout_seconds=timeout_seconds,
            use_docker=use_docker,
            use_daytona=use_daytona,
            docker_image=docker_image,
            docker_cwd=docker_cwd,
            docker_volumes=docker_volumes,
            docker_run_args=docker_run_args,
            data_in_image=data_in_image,
            daytona_image=daytona_image,
            daytona_cwd=daytona_cwd,
            daytona_sync_dirs=daytona_sync_dirs,
            overwrite=overwrite,
        )

        task_success = task.success_criteria(trace)
        if output_file:
            from infuse.runners.manifest import write_manifest
            write_manifest(
                Path(output_file), task_id=task.task_id, model=model_name, model_config=model_config,
                attack_config=attack_config, injection=injection_record, obs_level=obs_level,
                attack_overrides=attack_overrides, defense_name=defense_name, resolution_strategy=resolution_strategy,
                docker_image=docker_image if use_docker else None, result=result,
                extra={**(run_metadata or {}), "verifier_baseline": verifier_baseline},
            )
        touched = trace.get_touched_objects()
        attacked = trace.get_attacked_objects()

        print(f"\n{'=' * 60}", file=sys.stderr)
        print("COMPLETED", file=sys.stderr)
        print(f"{'=' * 60}", file=sys.stderr)
        print(f"Status: {result.get('exit_status')}", file=sys.stderr)
        print(f"Success: {result.get('success')} (criteria: {task_success})", file=sys.stderr)
        print(f"Events: {len(trace.events)}", file=sys.stderr)
        print(f"Cost: ${result.get('cost', 0):.4f} | Steps: {result.get('n_steps', 0)}", file=sys.stderr)
        if touched:
            print(f"Touched: {len(touched)} objects", file=sys.stderr)
            for obj in touched[:5]:
                print(f"  - {obj.get('object_id')} ({obj.get('touch_count')}x)", file=sys.stderr)
        if attacked:
            print(f"Attacked: {len(attacked)} objects", file=sys.stderr)
            for obj in attacked[:5]:
                print(f"  - {obj.get('object_id')} at step {obj.get('step')}", file=sys.stderr)

        return {
            "status": "completed" if result.get("success") else "error",
            "task_id": task.task_id,
            "task_category": task.category,
            "exit_status": result.get("exit_status"),
            "result": result.get("result", ""),
            "success": result.get("success", False),
            "task_success": task_success,
            "cost": result.get("cost", 0.0),
            "api_calls": result.get("api_calls", 0),
            "n_steps": result.get("n_steps", 0),
            "output_file": str(output_file),
            "trace": {
                "task_id": trace.task_id,
                "event_count": len(trace.events),
                "surfaces_touched": list({e.surface.value for e in trace.events}),
                "touched_objects": touched,
                "touched_objects_summary": {
                    "total": len(touched),
                    "unique": len({obj.get("object_id") for obj in touched if obj.get("object_id")}),
                },
                "attacked_objects": attacked,
                "attacked_objects_summary": {
                    "total": len(attacked),
                    "unique": len({obj.get("object_id") for obj in attacked if obj.get("object_id")}),
                },
                "events": [
                    {
                        "surface": e.surface.value,
                        "step": e.step,
                        "path": e.path,
                        "content_preview": e.content[:100] if e.content else "",
                    }
                    for e in trace.events
                ],
            },
            "error": result.get("error"),
        }

    except Exception as e:
        print(f"\n{'=' * 60}", file=sys.stderr)
        print("ERROR", file=sys.stderr)
        print(f"{'=' * 60}", file=sys.stderr)
        print(f"{e}", file=sys.stderr)
        traceback.print_exc()
        return {
            "status": "error",
            "task_id": task.task_id,
            "error": str(e),
            "trace": {"task_id": trace.task_id, "event_count": len(trace.events)},
            "output_file": str(output_file) if output_file else None,
        }

    finally:
        if cleanup_needed and tasks_root_for_cleanup and task_id_for_cleanup:
            run_cleanup_script(tasks_root_for_cleanup, task_id_for_cleanup)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Run a single agent test")

    task_group = parser.add_mutually_exclusive_group(required=True)
    task_group.add_argument("--task-id", type=str, help="Task ID ('task_N' for test_tasks, integer 1-26 for legacy)")
    task_group.add_argument("--template", help="Path to task template JSON (legacy)")

    parser.add_argument("--task-index", type=int, default=0, help="Task index (legacy)")
    parser.add_argument("--task-dir", help="Directory containing tasks (defaults to test_tasks/)")
    parser.add_argument("--attack-id", type=int, help="Attack ID from ATTACK_TEMPLATES.json")
    parser.add_argument("--attack-config", help="Path to attack config JSON")
    parser.add_argument("--attack-type", choices=["single", "multi"], help="Attack type")
    parser.add_argument("--attack-surface", help="Surface for single-surface attack")
    parser.add_argument("--attack-payload", help="Payload for single-surface attack")
    parser.add_argument("--injection", help="Path to injection YAML (legacy)")
    parser.add_argument("--obs-level", choices=["default", "troubleshoot", "gcg"], default="default",
                        help="Observation level for attack template formatting")
    parser.add_argument("--attack-overrides", type=json.loads, default=None, metavar="JSON",
                        help='JSON dict overriding attack config fields, e.g. \'{"inject_position": "prepend", "inject_prefix": "..."}\'.'
                             f' Allowed keys: {sorted(_OVERRIDE_SCHEMA)}')
    parser.add_argument("--model", help="Model name (e.g., gpt-4, anthropic/claude-3-5-sonnet)")
    parser.add_argument("--model-class", help="Model class (e.g., anthropic, litellm, openrouter)")
    parser.add_argument("--output-dir", default="./results", help="Output directory")
    parser.add_argument("--data-root", help="Root directory for task data")
    parser.add_argument("--work-root", help="Root directory for work")
    parser.add_argument("--timeout", type=int, help="Timeout in seconds")
    parser.add_argument("--cost-limit", type=float, help="Max cost in USD")

    runtime_group = parser.add_mutually_exclusive_group()
    runtime_group.add_argument("--use-docker", action="store_true", help="Run in Docker")
    runtime_group.add_argument("--use-daytona", action="store_true", help="Run in Daytona sandbox")

    parser.add_argument("--docker-image", default="agent-bench-base:latest", help="Docker image")
    parser.add_argument("--daytona-image", default=None, help="Daytona sandbox image")
    parser.add_argument("--overwrite", action="store_true", help="Re-run even if trajectory already exists")
    parser.add_argument("--defense", default=None, help="Defense name (e.g. delimiter_isolation, input_filter)")

    args = parser.parse_args()

    task = None
    if args.template:
        with open(args.template) as f:
            tasks_data = json.load(f)
        if args.task_index >= len(tasks_data):
            raise ValueError(f"Task index {args.task_index} out of range")
        from infuse.tasks.task_suite import load_benign_tasks
        tasks = load_benign_tasks()
        task = tasks[args.task_index] if args.task_index < len(tasks) else None
        task_id = task.task_id if task else None
    else:
        task_id = args.task_id

    attack_config = None
    print(f"Attack ID: {args.attack_id}", file=sys.stderr)
    if args.attack_id:
        from infuse.injection import AttackSpec
        attack_config = AttackSpec.load(str(args.attack_id), strict=False).raw
        print(f"✓ Loaded attack config: {attack_config.get('attack', {}).get('name', 'Unknown')}", file=sys.stderr)

    model_config = {"model_class": args.model_class} if args.model_class else None

    result = run_single_test_with_minisweagent(
        task_id=task_id,
        task=task,
        attack_config=attack_config,
        model_name=args.model,
        model_config=model_config,
        output_dir=args.output_dir,
        data_root=args.data_root,
        work_root=args.work_root,
        timeout_seconds=args.timeout,
        cost_limit=args.cost_limit,
        use_docker=args.use_docker,
        docker_image=args.docker_image,
        use_daytona=args.use_daytona,
        daytona_image=args.daytona_image,
        injection_path=args.injection,
        task_dir=args.task_dir,
        overwrite=args.overwrite,
        obs_level=args.obs_level,
        attack_overrides=args.attack_overrides,
        defense_name=args.defense,
    )

    PERMANENT_FAILURE_TYPES = {
        "AuthenticationError",
        "NotFoundError",
        "PermissionDeniedError",
        "BadRequestError",
    }
    exit_status = result.get("exit_status", "")
    if result.get("task_success"):
        sys.exit(0)
    elif exit_status in PERMANENT_FAILURE_TYPES:
        sys.exit(2)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
