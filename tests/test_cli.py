import json

import pytest

from infuse.cli import build_parser, compat_matrix, main
from tests.conftest import ATTACK_IDS, TASK_IDS


def test_help_for_every_subcommand(capsys):
    for argv in (["--help"], ["run", "--help"], ["batch", "--help"], ["judge", "--help"], ["attacks", "--help"]):
        with pytest.raises(SystemExit) as e:
            main(argv)
        assert e.value.code == 0


def test_batch_dry_run_cell_count(tmp_path, capsys, monkeypatch):
    from infuse import paths
    monkeypatch.setattr(paths, "DATA_ROOT", tmp_path)
    rc = main(["batch", "--attacks", "1,2", "--tasks", "1-3", "--models", "m1,m2", "--defenses", "none,delimiter_isolation",
               "--dry-run", "--results-dir", str(tmp_path)])
    assert rc == 0
    err = capsys.readouterr().err
    assert "24 cells" in err and "24 to run" in err


def test_batch_resumes(tmp_path, capsys):
    from infuse import paths
    (paths.attack_results_dir(1, 1, "m1", tmp_path)).mkdir(parents=True)
    (paths.attack_results_dir(1, 1, "m1", tmp_path) / "0_task_1.traj.json").write_text("{}")
    main(["batch", "--attacks", "1", "--tasks", "1,2", "--models", "m1", "--dry-run", "--results-dir", str(tmp_path)])
    assert "1 already done, 1 to run" in capsys.readouterr().err


def test_experiment_manifests_parse():
    from infuse import paths
    from infuse.runners.batch import BatchSpec
    names = sorted(p.stem for p in paths.EXPERIMENTS_DIR.glob("*.yaml"))
    assert {"main_grid", "benign", "defense_grid", "multi_surface"} <= set(names)
    for n in names:
        spec = BatchSpec.from_experiment(n)
        assert spec.tasks and spec.models
        assert spec.cells()


def test_compat_matrix_every_pair_resolves():
    m = compat_matrix("task_order")
    assert set(m) == {a.split("_", 1)[1] for a in ATTACK_IDS}
    missing = [(a, t) for a, row in m.items() for t, s in row.items() if not s]
    assert not missing, f"{len(missing)} attack×task pairs have no injection target: {missing[:10]}"


def test_attacks_list_json(capsys):
    assert main(["attacks", "list", "--json"]) == 0
    rows = json.loads(capsys.readouterr().out)
    assert len(rows) == len(ATTACK_IDS)


def test_task_prefix_is_on_by_default():
    from infuse.runners.batch import BatchSpec, build_overrides
    spec = BatchSpec(attacks=["1"], tasks=["1", "31"], models=["m"])
    assert spec.task_prefix is True
    ov1 = build_overrides(spec, "1")
    assert ov1["inject_prefix"].startswith("[SECURITY ALERT]")          # table entry for task 1
    assert "inject_prefix" not in build_overrides(spec, "31")           # no entry → attack's own prefix
    spec.task_prefix = False
    assert "inject_prefix" not in build_overrides(spec, "1")


def test_no_task_prefix_flag_overrides_experiment():
    from infuse.runners.batch import BatchSpec
    assert BatchSpec.from_experiment("main_grid").task_prefix is True
    assert BatchSpec.from_experiment("main_grid", task_prefix=False).task_prefix is False
