"""
LiteLLM Open-Weight Model — routes open-weight models through LiteLLM.

Supports multiple backends:
  - "openai/<model>"          → local vLLM / TGI behind an OpenAI-compatible API
  - "huggingface/<model>"     → Hugging Face Inference Endpoints
  - "together_ai/<model>"     → Together AI
  - "anyscale/<model>"        → Anyscale Endpoints
  - "deepinfra/<model>"       → DeepInfra
  - "ollama/<model>"          → local Ollama

Examples:
    # Local vLLM through LiteLLM
    model = LiteLLMOpenWeightModel(
        model_name="openai/meta-llama/Llama-3.1-70B-Instruct",
        api_base="http://localhost:8000/v1",
    )

    # Together AI
    model = LiteLLMOpenWeightModel(
        model_name="together_ai/meta-llama/Llama-3.1-70B-Instruct",
    )
"""

import json
import logging
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import litellm
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_not_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from minisweagent.models import GLOBAL_MODEL_STATS

logger = logging.getLogger("litellm_openweight_model")


@dataclass
class LiteLLMOpenWeightModelConfig:
    model_name: str
    api_base: str | None = os.getenv("OPENWEIGHT_API_BASE", None)
    """Override the API base URL (e.g., for local vLLM / TGI servers)."""
    api_key: str | None = os.getenv("OPENWEIGHT_API_KEY", None)
    """API key — needed for hosted providers (Together, DeepInfra, etc.)."""
    model_kwargs: dict[str, Any] = field(default_factory=dict)
    litellm_model_registry: Path | str | None = os.getenv("LITELLM_MODEL_REGISTRY_PATH")
    cost_per_million_input_tokens: float = 0.0
    cost_per_million_output_tokens: float = 0.0
    """Fallback per-token pricing when LiteLLM cannot determine cost."""


class LiteLLMOpenWeightModel:
    """Routes open-weight model calls through LiteLLM.

    Implements the minisweagent Model protocol (config, cost, n_calls, query, get_template_vars).
    """

    def __init__(self, **kwargs):
        self.config = LiteLLMOpenWeightModelConfig(**kwargs)
        self.cost = 0.0
        self.n_calls = 0

        if os.getenv("LITELLM_LOG") == "DEBUG" or os.getenv("LITELLM_DEBUG") == "true":
            litellm.set_verbose = True
            logger.setLevel(logging.DEBUG)
            logging.getLogger("litellm").setLevel(logging.DEBUG)

        if self.config.litellm_model_registry and Path(self.config.litellm_model_registry).is_file():
            litellm.utils.register_model(
                json.loads(Path(self.config.litellm_model_registry).read_text())
            )

        # For local servers (vLLM/TGI), drop unsupported params by default
        self.config.model_kwargs.setdefault("drop_params", True)

        # Auto-register model with zero cost if not in litellm's registry.
        # This is common for local/self-hosted models (vLLM, Ollama, TGI) that
        # litellm doesn't have pricing data for, which would otherwise raise
        # "This model isn't mapped yet" before making any API call.
        model_key = self.config.model_name
        if model_key not in litellm.model_cost:
            provider = model_key.split("/")[0] if "/" in model_key else "openai"
            litellm.utils.register_model({
                model_key: {
                    "max_tokens": 8192,
                    "input_cost_per_token": self.config.cost_per_million_input_tokens / 1_000_000,
                    "output_cost_per_token": self.config.cost_per_million_output_tokens / 1_000_000,
                    "litellm_provider": provider,
                    "mode": "chat",
                }
            })
            logger.debug(f"Auto-registered model '{model_key}' in litellm registry (zero cost)")

    @retry(
        stop=stop_after_attempt(int(os.getenv("MSWEA_MODEL_RETRY_STOP_AFTER_ATTEMPT", "10"))),
        wait=wait_exponential(multiplier=1, min=4, max=60),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        retry=retry_if_not_exception_type(
            (
                litellm.exceptions.AuthenticationError,
                litellm.exceptions.NotFoundError,
                litellm.exceptions.PermissionDeniedError,
                KeyboardInterrupt,
            )
        ),
    )
    def _query(self, messages: list[dict[str, str]], **kwargs):
        call_kwargs: dict[str, Any] = {
            "model": self.config.model_name,
            "messages": messages,
            **(self.config.model_kwargs | kwargs),
        }

        if self.config.api_base:
            call_kwargs["api_base"] = self.config.api_base
        if self.config.api_key:
            call_kwargs["api_key"] = self.config.api_key

        logger.debug(
            f"litellm.completion model={self.config.model_name} "
            f"api_base={self.config.api_base}"
        )

        try:
            return litellm.completion(**call_kwargs)
        except litellm.exceptions.AuthenticationError as e:
            e.message += (
                " Set the API key for your provider via the appropriate env var "
                "(e.g. TOGETHER_API_KEY, OPENWEIGHT_API_KEY) or pass api_key= directly."
            )
            raise
        except litellm.exceptions.BadRequestError as e:
            error_msg = str(e)
            if "LLM Provider NOT provided" in error_msg:
                logger.error(
                    f"Model name format error: '{self.config.model_name}'. "
                    f"For open-weight models use a provider prefix, e.g. "
                    f"'openai/meta-llama/Llama-3.1-70B-Instruct' (local vLLM), "
                    f"'together_ai/meta-llama/Llama-3.1-70B-Instruct', "
                    f"'huggingface/meta-llama/Llama-3.1-70B-Instruct'."
                )
            raise

    def _estimate_cost(self, usage: dict) -> float:
        """Fallback cost estimate when LiteLLM has no pricing data."""
        prompt_tokens = usage.get("prompt_tokens", 0) if usage else 0
        completion_tokens = usage.get("completion_tokens", 0) if usage else 0
        input_cost = (prompt_tokens / 1_000_000) * self.config.cost_per_million_input_tokens
        output_cost = (completion_tokens / 1_000_000) * self.config.cost_per_million_output_tokens
        return input_cost + output_cost

    def query(self, messages: list[dict[str, str]], **kwargs) -> dict:
        response = self._query(messages, **kwargs)

        # Try LiteLLM's built-in cost calculator; fall back to manual estimate
        try:
            cost = litellm.cost_calculator.completion_cost(response)
        except Exception:
            usage = response.usage.model_dump() if hasattr(response, "usage") and response.usage else {}
            cost = self._estimate_cost(usage)
            if cost == 0.0:
                logger.debug(
                    f"No cost data for {self.config.model_name}; "
                    f"set cost_per_million_input/output_tokens for tracking."
                )

        assert cost >= 0.0, f"Cost is negative: {cost}"
        self.n_calls += 1
        self.cost += cost
        GLOBAL_MODEL_STATS.add(cost)

        content = response.choices[0].message.content or ""

        return {
            "content": content,
            "extra": {
                "response": response.model_dump(),
                "cost": cost,
            },
        }

    def get_template_vars(self) -> dict[str, Any]:
        return asdict(self.config) | {"n_model_calls": self.n_calls, "model_cost": self.cost}
