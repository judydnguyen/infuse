from pathlib import Path

from infuse import paths


def test_repo_layout_exists():
    for p in (paths.BENCHMARK_ROOT, paths.TASKS_DIR, paths.ATTACKS_DIR, paths.CONFIGS_DIR, paths.TEMPLATES_DIR):
        assert p.is_dir(), p
    assert paths.MODELS_YAML.is_file()
    assert paths.AGENT_DEFAULT_CONFIG.is_file()


def test_id_normalisation():
    assert paths.task_dir("task_3") == paths.task_dir(3) == paths.TASKS_DIR / "task_3"
    assert paths.attack_config_path("attack_101") == paths.ATTACKS_DIR / "attack_101" / "config.toml"


def test_results_dir_precedence(tmp_path, monkeypatch):
    monkeypatch.setattr(paths, "DATA_ROOT", tmp_path)
    assert paths.results_dir() == tmp_path
    assert paths.results_dir("multi_surface") == tmp_path / "multi_surface"
    assert paths.results_dir("/abs/elsewhere") == Path("/abs/elsewhere")


def test_result_layout_matches_legacy(tmp_path):
    assert paths.attack_results_dir(1, "task_2", "gpt-4o-mini", tmp_path) == tmp_path / "attack_task" / "1" / "2" / "gpt-4o-mini"
    assert paths.benign_results_dir("meta-llama/Llama-3.1-8B-Instruct", 2, tmp_path) == \
        tmp_path / "benign_task" / "meta-llama_Llama-3.1-8B-Instruct" / "task_2"
