"""Single source of truth for every filesystem location the benchmark uses.

Nothing else in the package may build a path from ``Path(__file__)`` or from a
hardcoded machine-specific string. Override points, in priority order:

1. explicit function arguments / CLI flags (``--results-dir``, ``--tasks-root``)
2. environment variables (loaded from ``.env`` at the repo root if present)
3. the defaults below (repo-relative; results default to ``<repo>/results``)
"""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

PACKAGE_ROOT = Path(__file__).resolve().parent
REPO_ROOT = PACKAGE_ROOT.parent

# .env is optional; environment variables already set take precedence.
load_dotenv(REPO_ROOT / ".env", override=False)

# --- benchmark definition (versioned with the repo) -------------------------
BENCHMARK_ROOT = REPO_ROOT / "benchmark"
TASKS_DIR = BENCHMARK_ROOT / "tasks"
ATTACKS_DIR = BENCHMARK_ROOT / "attacks"
CONFIGS_DIR = BENCHMARK_ROOT / "configs"
TEMPLATES_DIR = BENCHMARK_ROOT / "templates"
EXPERIMENTS_DIR = BENCHMARK_ROOT / "experiments"
MODELS_YAML = CONFIGS_DIR / "models.yaml"
TASK_PREFIX_JSON = CONFIGS_DIR / "task_inject_prefixes.json"
EVALS_DIR = TEMPLATES_DIR / "evals"

# --- agent config -------------------------------------------------------------
AGENT_CONFIG_DIR = PACKAGE_ROOT / "agents" / "minisweagent" / "config"
AGENT_DEFAULT_CONFIG = AGENT_CONFIG_DIR / "default.yaml"

# --- results (large, machine-specific, never versioned) -----------------------
DATA_ROOT = Path(os.getenv("DATA_ROOT_PATH") or (REPO_ROOT / "results")).expanduser()
HF_CACHE = Path(os.getenv("HF_HOME") or os.getenv("HUGGINGFACE_HUB_CACHE") or (Path.home() / ".cache" / "huggingface")).expanduser()


def results_dir(override: str | os.PathLike | None = None) -> Path:
    """Resolve the results base directory.

    ``override`` (from ``--results-dir``) wins. A relative override is placed
    under ``DATA_ROOT`` so that ``--results-dir multi_surface`` lands next to
    the canonical ``attack_task/`` tree, matching the legacy shell scripts.
    """
    if override is None:
        return DATA_ROOT
    p = Path(override).expanduser()
    return p if p.is_absolute() else DATA_ROOT / p


def task_dir(task_id: str | int) -> Path:
    return TASKS_DIR / _norm("task", task_id)


def attack_dir(attack_id: str | int) -> Path:
    return ATTACKS_DIR / _norm("attack", attack_id)


def attack_config_path(attack_id: str | int) -> Path:
    return attack_dir(attack_id) / "config.toml"


def task_overlay_path(task_id: str | int) -> Path:
    return task_dir(task_id) / "environment" / "overlays" / "benign.toml"


def benign_results_dir(model: str, task_id: str | int, base: Path | None = None) -> Path:
    """``<base>/benign_task/<model>/<task_id>/``"""
    return (base or DATA_ROOT) / "benign_task" / _safe(model) / _norm("task", task_id)


def attack_results_dir(attack_id: str | int, task_id: str | int, model: str, base: Path | None = None) -> Path:
    """``<base>/attack_task/<attack_id>/<task_id>/<model>/`` (legacy-compatible layout)."""
    return (base or DATA_ROOT) / "attack_task" / str(_id(attack_id)) / str(_id(task_id)) / _safe(model)


def _id(value: str | int) -> str:
    s = str(value)
    for prefix in ("task_", "attack_"):
        if s.startswith(prefix):
            return s[len(prefix):]
    return s


def _norm(kind: str, value: str | int) -> str:
    return f"{kind}_{_id(value)}"


def _safe(model: str) -> str:
    return model.replace("/", "_")


__all__ = [n for n in dir() if n.isupper() or n in {
    "results_dir", "task_dir", "attack_dir", "attack_config_path", "task_overlay_path",
    "benign_results_dir", "attack_results_dir",
}]
