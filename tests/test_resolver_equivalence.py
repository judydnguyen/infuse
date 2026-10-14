"""Under ``task_order`` the new resolver must choose exactly what the legacy injector chose,
for every attack × task pair, in both single and multi mode. Resolution is read-only, so we
point both at the shipped ``environment/app`` directories."""
import logging

import pytest

from infuse import paths
from infuse.injection import AttackSpec, TaskSurfaces
from infuse.injection._legacy_injector import TestTaskAttackInjector
from infuse.injection.resolver import resolve, select
from tests.conftest import ATTACK_IDS, TASK_IDS

logging.getLogger("infuse.injection._legacy_injector").setLevel(logging.ERROR)
_LEGACY = TestTaskAttackInjector(paths.TASKS_DIR)


def _legacy_targets(attack, task, mode):
    cfg = _LEGACY.load_attack_config(attack.split("_", 1)[1])
    cfg["attack"].setdefault("surfaces", {})["mode"] = mode
    workdir = paths.task_dir(task) / "environment" / "app"
    resolved = _LEGACY.resolve_surfaces(cfg, _LEGACY.load_benign_overlay(task), workdir)
    if mode == "multi":
        picks = _LEGACY.select_all_target_files(resolved, cfg)
    else:
        one = _LEGACY.select_target_file(resolved, cfg)
        picks = [one] if one else []
    return [(s, str(p)) for p, s in picks]


def _new_targets(attack, task, mode):
    spec = AttackSpec.load(attack, strict=False)
    spec.mode = mode
    ts = TaskSurfaces.load(task, strict=False)
    workdir = paths.task_dir(task) / "environment" / "app"
    return [(c.surface.value, str(c.path)) for c in select(resolve(spec, ts, workdir, "task_order"), mode)]


@pytest.mark.parametrize("mode", ["single", "multi"])
@pytest.mark.parametrize("task", TASK_IDS)
@pytest.mark.parametrize("attack", ATTACK_IDS)
def test_same_targets_as_legacy(attack, task, mode):
    assert _new_targets(attack, task, mode) == _legacy_targets(attack, task, mode)


def test_attack_preference_honours_primary_order():
    """A task that lists FILENAME before FILE_CONTENT: task_order picks FILENAME, attack_preference FILE_CONTENT."""
    from pathlib import Path
    from infuse.injection.spec import TaskSurfaces as TS
    from infuse.surfaces import InjectionSurface as S
    spec = AttackSpec.load(ATTACK_IDS[0], strict=False)
    assert spec.primary[0] is S.FILE_CONTENT
    ts = TS(task_id="synthetic", surfaces={S.FILENAME: ["a.py"], S.FILE_CONTENT: ["a.py"]})
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        (Path(d) / "a.py").write_text("x")
        assert resolve(spec, ts, Path(d), "task_order")[0].surface is S.FILENAME
        assert resolve(spec, ts, Path(d), "attack_preference")[0].surface is S.FILE_CONTENT
