"""This file provides convenience functions for selecting models.
You can ignore this file completely if you explicitly set your model in your run script.
"""

import copy
import importlib
import os
import threading

from minisweagent import Model


class GlobalModelStats:
    """Global model statistics tracker with optional limits."""

    def __init__(self):
        self._cost = 0.0
        self._n_calls = 0
        self._lock = threading.Lock()
        self.cost_limit = float(os.getenv("MSWEA_GLOBAL_COST_LIMIT", "0"))
        self.call_limit = int(os.getenv("MSWEA_GLOBAL_CALL_LIMIT", "0"))
        if (self.cost_limit > 0 or self.call_limit > 0) and not os.getenv("MSWEA_SILENT_STARTUP"):
            print(f"Global cost/call limit: ${self.cost_limit:.4f} / {self.call_limit}")

    def add(self, cost: float) -> None:
        """Add a model call with its cost, checking limits."""
        with self._lock:
            self._cost += cost
            self._n_calls += 1
        if 0 < self.cost_limit < self._cost or 0 < self.call_limit < self._n_calls + 1:
            raise RuntimeError(f"Global cost/call limit exceeded: ${self._cost:.4f} / {self._n_calls + 1}")

    @property
    def cost(self) -> float:
        return self._cost

    @property
    def n_calls(self) -> int:
        return self._n_calls


GLOBAL_MODEL_STATS = GlobalModelStats()


def get_model(input_model_name: str | None = None, config: dict | None = None) -> Model:
    """Get an initialized model object from any kind of user input or settings."""
    resolved_model_name = get_model_name(input_model_name, config)
    if config is None:
        config = {}
    config = copy.deepcopy(config)
    config["model_name"] = resolved_model_name

    model_class = get_model_class(resolved_model_name, config.pop("model_class", ""))

    if (from_env := os.getenv("MSWEA_MODEL_API_KEY")) and not str(type(model_class)).endswith("DeterministicModel"):
        config.setdefault("model_kwargs", {})["api_key"] = from_env

    # AGENT_MODEL_GATEWAY=1: route OpenAI-family models through the custom
    # OpenAI-compatible gateway (X-API-Key auth), mirroring the defense-model
    # gateway path in runners/run_test_task.py. The plain model name is kept so
    # result folders and litellm cost lookup match direct-API runs. Applied here
    # (not in runners/common.get_model_config, which nothing calls) because this
    # is the single point every runner passes through. AGENT_RPM_LIMIT paces
    # requests per process.
    if os.getenv("AGENT_MODEL_GATEWAY") == "1" and not any(
        s in resolved_model_name.lower() for s in ["anthropic", "claude", "gemini", "openai/", "/"]
    ):
        config["model_kwargs"] = {
            **config.get("model_kwargs", {}),
            "custom_llm_provider": "openai",
            "api_base": os.environ["GATEWAY_API_BASE"].rstrip("/"),
            "api_key": "gateway",
            "extra_headers": {"X-API-Key": os.environ["GATEWAY_API_KEY"]},
        }

    if (
        any(s in resolved_model_name.lower() for s in ["anthropic", "sonnet", "opus", "claude"])
        and "set_cache_control" not in config
    ):
        # Select cache control for Anthropic models by default
        config["set_cache_control"] = "default_end"

    # Optional per-process request pacing for any litellm-served model.
    if os.getenv("AGENT_RPM_LIMIT") and "rpm_limit" not in config:
        config["rpm_limit"] = int(os.environ["AGENT_RPM_LIMIT"])

    return model_class(**config)


def get_model_name(input_model_name: str | None = None, config: dict | None = None) -> str:
    """Get a model name from any kind of user input or settings."""
    if config is None:
        config = {}
    if input_model_name:
        return input_model_name
    if from_config := config.get("model_name"):
        return from_config
    if from_env := os.getenv("MSWEA_MODEL_NAME"):
        return from_env
    raise ValueError("No default model set. Please run `mini-extra config setup` to set one.")


_MODEL_CLASS_MAPPING = {
    "anthropic": "minisweagent.models.anthropic.AnthropicModel",
    "litellm": "minisweagent.models.litellm_model.LitellmModel",
    "openrouter": "minisweagent.models.openrouter_model.OpenRouterModel",
    "portkey": "minisweagent.models.portkey_model.PortkeyModel",
    "deterministic": "minisweagent.models.test_models.DeterministicModel",
    "vllm": "infuse.agents.openweight.vllm_model.VLLMModel",
    "litellm_openweight": "infuse.agents.openweight.litellm_openweight_model.LiteLLMOpenWeightModel",
}


def get_model_class(model_name: str, model_class: str = "") -> type:
    """Select the best model class.

    If a model_class is provided (as shortcut name, or as full import path,
    e.g., "anthropic" or "minisweagent.models.anthropic.AnthropicModel"),
    it takes precedence over the `model_name`.
    Otherwise, the model_name is used to select the best model class.
    """
    if model_class:
        full_path = _MODEL_CLASS_MAPPING.get(model_class, model_class)
        try:
            module_name, class_name = full_path.rsplit(".", 1)
            module = importlib.import_module(module_name)
            return getattr(module, class_name)
        except (ValueError, ImportError, AttributeError):
            msg = f"Unknown model class: {model_class} (resolved to {full_path}, available: {_MODEL_CLASS_MAPPING})"
            raise ValueError(msg)

    # Auto-detect vLLM backend when VLLM_API_BASE is set and model looks like
    # an open-weight model (no known cloud provider prefix).
    lower = model_name.lower()
    _CLOUD_PREFIXES = ("gpt", "claude", "gemini", "o1-", "o3-", "o4-")
    if os.getenv("VLLM_API_BASE") and not any(lower.startswith(p) for p in _CLOUD_PREFIXES):
        from infuse.agents.openweight.vllm_model import VLLMModel
        return VLLMModel

    # Default to LitellmModel
    from minisweagent.models.litellm_model import LitellmModel

    return LitellmModel
