"""``<trajectory>.manifest.json``: everything needed to explain or reproduce one run."""
from __future__ import annotations

import datetime as _dt
import json
import subprocess
from pathlib import Path
from typing import Any

from infuse import __version__, paths


def git_sha() -> str | None:
    try:
        return subprocess.run(["git", "rev-parse", "HEAD"], cwd=paths.REPO_ROOT, capture_output=True,
                              text=True, timeout=5, check=True).stdout.strip()
    except Exception:
        return None


def manifest_path(traj_path: Path) -> Path:
    name = traj_path.name
    if name.endswith(".traj.json"):
        name = name[: -len(".traj.json")]
    else:
        name = traj_path.stem
    return traj_path.with_name(name + ".manifest.json")


def write_manifest(traj_path: Path, *, task_id: str, model: str | None, model_config: dict | None,
                   attack_config: dict | None, injection, obs_level: str, attack_overrides: dict | None,
                   defense_name: str | None, resolution_strategy: str, docker_image: str | None,
                   result: dict | None, extra: dict | None = None) -> Path:
    attack = (attack_config or {}).get("attack", {}) if attack_config else {}
    data: dict[str, Any] = {
        "sab_version": __version__,
        "git_sha": git_sha(),
        "written_at": _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds"),
        "task_id": task_id,
        "attack_id": str(attack.get("id")) if attack else None,
        "attack_name": attack.get("name") if attack else None,
        "model": model,
        "model_class": (model_config or {}).get("model_class"),
        "defense": defense_name or "none",
        "obs_level": obs_level,
        "attack_overrides": attack_overrides or {},
        "resolution_strategy": resolution_strategy,
        "docker_image": docker_image,
        "injection": injection.to_dict() if injection is not None else None,
        "outcome": {
            "exit_status": (result or {}).get("exit_status"),
            "success": (result or {}).get("success"),
            "cost_usd": (result or {}).get("cost"),
            "n_steps": (result or {}).get("n_steps"),
            "test_sh_passed": (result or {}).get("test_sh_passed"),
        },
        "trajectory": traj_path.name,
    }
    if extra:
        data.update(extra)
    out = manifest_path(traj_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
    return out


__all__ = ["write_manifest", "manifest_path", "git_sha"]
