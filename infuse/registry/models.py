"""Model registry and resolution.

* ``benchmark/configs/models.yaml`` lists every model the benchmark knows about:
  API models (provider, model_class, cost defaults, aliases) and open-weight
  models (vLLM serving options). :func:`load_models` reads it.
* :func:`agent_model_config` turns a user-facing model name into the
  ``(model_name, model_config)`` pair the vendored agent expects.
* :func:`defense_model_fn` builds the ``prompt -> text`` callable LLM-backed
  defenses use, honouring the same gateway / vLLM / pacing env vars as agents.
"""
from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from functools import lru_cache
from typing import Any, Callable

import yaml

from infuse import paths


@lru_cache(maxsize=1)
def load_models() -> dict[str, dict[str, Any]]:
    with open(paths.MODELS_YAML) as f:
        data = yaml.safe_load(f) or {}
    return data.get("models", {}) or {}


def _alias_map() -> dict[str, str]:
    out: dict[str, str] = {}
    for key, cfg in load_models().items():
        out[key.lower()] = cfg.get("model_id", key)
        for a in cfg.get("aliases", []) or []:
            out[str(a).lower()] = cfg.get("model_id", key)
    return out


def resolve_model_name(name: str) -> str:
    """Registry key or alias -> canonical model id; unknown names pass through unchanged."""
    return _alias_map().get(name.lower(), name)


def model_entry(name: str) -> dict[str, Any] | None:
    canonical = resolve_model_name(name)
    for key, cfg in load_models().items():
        if key.lower() == name.lower() or cfg.get("model_id") == canonical:
            return cfg
    return None


def is_open_weight(name: str) -> bool:
    entry = model_entry(name)
    if entry is not None:
        return entry.get("provider", "vllm") == "vllm" or "tensor_parallel_size" in entry
    return "/" in name and not name.lower().startswith(("openai/", "anthropic/", "gemini/"))


def agent_model_config(name: str, model_class: str | None = None) -> tuple[str, dict[str, Any] | None]:
    """``(model_name, model_config)`` for the agent; open-weight models default to the vLLM class."""
    canonical = resolve_model_name(name)
    entry = model_entry(name) or {}
    cls = model_class or entry.get("model_class") or ("vllm" if is_open_weight(canonical) else None)
    cfg: dict[str, Any] = {}
    if cls:
        cfg["model_class"] = cls
    if cls == "vllm":
        api_base = os.getenv("VLLM_API_BASE") or (f"http://localhost:{entry['port']}/v1" if entry.get("port") else None)
        if api_base:
            cfg["api_base"] = api_base
    return canonical, (cfg or None)


def default_cost_limit(name: str, fallback: float = 0.005) -> float:
    entry = model_entry(name) or {}
    return float(entry.get("default_cost_limit", fallback))


def defense_model_fn(defense_model: str) -> Callable[[str], str]:
    """A ``prompt -> completion`` callable for LLM-backed defenses.

    ``<name>-gateway`` or ``DEFENSE_MODEL_GATEWAY=1`` routes through the
    OpenAI-compatible gateway (``GATEWAY_API_BASE`` / ``GATEWAY_API_KEY``) with
    exponential back-off on 429/5xx. Otherwise the vendored model loader is used,
    with ``DEFENSE_VLLM_API_BASE`` and ``DEFENSE_MODEL_RPM`` applied when set.
    """
    if defense_model.endswith("-gateway") or os.environ.get("DEFENSE_MODEL_GATEWAY"):
        gw_model = defense_model[: -len("-gateway")] if defense_model.endswith("-gateway") else defense_model
        gw_base = os.environ["GATEWAY_API_BASE"].rstrip("/")
        gw_key = os.environ["GATEWAY_API_KEY"]

        def via_gateway(prompt: str) -> str:
            body = json.dumps({"model": gw_model, "temperature": 0.0,
                               "messages": [{"role": "user", "content": prompt}]}).encode()
            last: Exception | None = None
            for attempt in range(6):
                try:
                    req = urllib.request.Request(gw_base + "/chat/completions", data=body,
                                                 headers={"X-API-Key": gw_key, "Content-Type": "application/json"})
                    with urllib.request.urlopen(req, timeout=120) as r:
                        return json.loads(r.read())["choices"][0]["message"]["content"]
                except urllib.error.HTTPError as e:
                    last = e
                    if e.code in (429, 500, 502, 503, 504):
                        time.sleep(min(60, 4 * (2 ** attempt)))
                        continue
                    raise
            raise last  # type: ignore[misc]
        return via_gateway

    from infuse.agents.minisweagent.models import get_model
    cfg: dict[str, Any] = {}
    if base := os.environ.get("DEFENSE_VLLM_API_BASE"):
        cfg.update(api_base=base, model_class="vllm")
    if rpm := os.environ.get("DEFENSE_MODEL_RPM"):
        cfg["rpm_limit"] = int(rpm)
    judge = get_model(resolve_model_name(defense_model), config=cfg or None)

    def via_agent_loader(prompt: str) -> str:
        return judge.query([{"role": "user", "content": prompt}]).get("content", "")
    return via_agent_loader


__all__ = ["load_models", "resolve_model_name", "model_entry", "is_open_weight", "agent_model_config",
           "default_cost_limit", "defense_model_fn"]
