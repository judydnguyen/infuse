"""Every shipped attack config and task overlay must load under strict validation."""
import pytest

from infuse.injection import AttackSpec, TaskSurfaces
from infuse.surfaces import InjectionSurface
from tests.conftest import ATTACK_IDS, TASK_IDS


@pytest.mark.parametrize("attack", ATTACK_IDS)
def test_attack_spec_strict(attack):
    spec = AttackSpec.load(attack)
    assert spec.id == attack.split("_", 1)[1]
    assert spec.supported, "attack must support at least one injection surface"
    assert all(isinstance(s, InjectionSurface) for s in spec.supported)
    assert spec.payload_template.strip()


@pytest.mark.parametrize("task", TASK_IDS)
def test_task_surfaces_strict(task):
    ts = TaskSurfaces.load(task)
    assert ts.declared, "task must declare at least one injection surface"
    for s, files in ts.surfaces.items():
        assert isinstance(s, InjectionSurface)
        assert files


def test_overrides_round_trip():
    spec = AttackSpec.load(ATTACK_IDS[0])
    new = spec.with_overrides({"inject_position": "prepend", "inject_prefix": "X: ", "surfaces_mode": "multi"})
    assert (new.inject_position, new.inject_prefix, new.mode) == ("prepend", "X: ", "multi")
    assert spec.inject_position != "prepend" or spec.mode == "single"  # original untouched
    with pytest.raises(Exception):
        spec.with_overrides({"bogus": 1})
