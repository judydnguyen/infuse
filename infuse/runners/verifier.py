"""Attack verifiers (``attacks/attack_<id>/tests/test.sh`` or legacy ``solution.sh``).

A verifier inspects the container after the agent ran and exits 0 when it finds
evidence the attack succeeded. Many legacy verifiers grep the filesystem for
strings that also occur in the planted payload itself, so they fire even when
the agent did nothing. :func:`baseline` runs the verifier on a *fresh* container
of the built image, before any agent step, and records that outcome so the
post-run result can be read as ``passed and not baseline_passed``.
"""
from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

from infuse import paths


def find_verifier(attack_id: str | int) -> Path | None:
    d = paths.attack_dir(attack_id)
    for cand in (d / "tests" / "test.sh", d / "solution.sh"):
        if cand.exists():
            return cand
    return None


def baseline(image: str, attack_id: str | int, injected_files=None, timeout: int = 120) -> dict[str, Any]:
    """Run the verifier in a throw-away container of *image* with NO agent activity.

    A correct verifier reports failure here: nothing was done except the payload
    injection itself. ``injected_files`` are excluded from on-disk checks, exactly
    as during a real run.
    """
    script = find_verifier(attack_id)
    if script is None:
        return {"available": False}
    lib = (paths.ATTACKS_DIR / "verifier_lib.sh").resolve()
    inj = ",".join(str(f) for f in (injected_files or []))
    env_prefix = (
        "VERIFIER_LIB=/tmp/verifier_lib.sh AGENT_ACTIONS=/dev/null "
        f"INJECTED_FILES=\"$(printf '%s' '{inj}' | tr , '\n')\" "
    )
    cmd = ["docker", "run", "--rm",
           "-v", f"{script.resolve()}:/tmp/attack_test.sh:ro",
           "-v", f"{lib}:/tmp/verifier_lib.sh:ro", "-w", "/app",
           image, "bash", "-c", f"{env_prefix} bash /tmp/attack_test.sh /app"]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return {"available": True, "script": script.name, "error": "timeout"}
    except FileNotFoundError:
        return {"available": True, "script": script.name, "error": "docker not found"}
    out = (r.stdout + r.stderr).strip()
    return {"available": True, "script": script.name, "passed": r.returncode == 0, "returncode": r.returncode,
            "output": out[-1000:]}


__all__ = ["find_verifier", "baseline"]
