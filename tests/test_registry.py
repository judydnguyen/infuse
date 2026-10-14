import pytest

from infuse.registry import DEFENSE_NAMES, agent_model_config, build_defense, load_models, needs_model, resolve_model_name


@pytest.mark.parametrize("name", [n for n in DEFENSE_NAMES if not needs_model(n)])
def test_model_free_defenses_build(name):
    assert build_defense(name) is not None


@pytest.mark.parametrize("name", [n for n in DEFENSE_NAMES if needs_model(n)])
def test_llm_defenses_require_model(name):
    with pytest.raises(ValueError):
        build_defense(name)


def test_unknown_defense():
    with pytest.raises(ValueError):
        build_defense("nope")


def test_models_yaml_entries_resolve():
    models = load_models()
    assert models
    for key, cfg in models.items():
        assert "model_id" in cfg, key
        name, mcfg = agent_model_config(key)
        assert name == cfg["model_id"]
        assert resolve_model_name(key) == cfg["model_id"]


def test_api_models_pass_through():
    assert agent_model_config("gpt-4o-mini") == ("gpt-4o-mini", None)
    assert agent_model_config("claude-haiku-4-5", "anthropic") == ("claude-haiku-4-5", {"model_class": "anthropic"})
