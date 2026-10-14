"""Scan: which attack verifiers fire on an injected-but-untouched task tree? (Docker required)

    python -m infuse.runners.verifier_scan [task_id]
"""
from __future__ import annotations

import logging
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from infuse import paths
from infuse.injection import AttackSpec, TaskSurfaces, inject
from infuse.runners.verifier import find_verifier


def scan(task_id: str = "task_1", image: str = "python:3.10-slim") -> dict[str, bool]:
    logging.disable(logging.WARNING)
    ts = TaskSurfaces.load(task_id)
    src = paths.task_dir(task_id) / "environment" / "app"
    out: dict[str, bool] = {}
    for d in sorted(paths.ATTACKS_DIR.glob("attack_*"), key=lambda p: int(p.name.split("_")[1])):
        aid = d.name.split("_")[1]
        script = find_verifier(aid)
        if script is None:
            continue
        tmp = Path(tempfile.mkdtemp(prefix=f"vscan_{aid}_"))
        work = tmp / "app"
        shutil.copytree(src, work)
        rec = inject(AttackSpec.load(aid), ts, work)
        lib = (paths.ATTACKS_DIR / "verifier_lib.sh").resolve()
        inj = ",".join(rec.written_files)
        env_prefix = ("VERIFIER_LIB=/tmp/verifier_lib.sh AGENT_ACTIONS=/dev/null "
                      f"INJECTED_FILES=\"$(printf '%s' '{inj}' | tr , '\n')\" ")
        r = subprocess.run(["docker", "run", "--rm", "-v", f"{work}:/app",
                            "-v", f"{script}:/tmp/t.sh:ro", "-v", f"{lib}:/tmp/verifier_lib.sh:ro", "-w", "/app",
                            image, "bash", "-c", f"{env_prefix} bash /tmp/t.sh /app"],
                           capture_output=True, text=True, timeout=180)
        out[aid] = r.returncode == 0
        shutil.rmtree(tmp, ignore_errors=True)
    return out


def main(argv: list[str] | None = None) -> int:
    task = (argv or sys.argv[1:] or ["task_1"])[0]
    res = scan(paths._norm("task", task))
    fp = [a for a, p in res.items() if p]
    print(f"{task}: {len(fp)}/{len(res)} verifiers pass with no agent action (false positives): {', '.join(fp)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
