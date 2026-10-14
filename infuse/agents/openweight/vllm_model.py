"""
vLLM Model — calls a self-hosted vLLM OpenAI-compatible server.

Start a vLLM server first:
    python -m vllm.entrypoints.openai.api_server \
        --model meta-llama/Llama-3.1-70B-Instruct \
        --tensor-parallel-size 4 \
        --port 8000

Then use this model class:
    model = VLLMModel(
        model_name="meta-llama/Llama-3.1-70B-Instruct",
        api_base="http://localhost:8000/v1",
    )
"""

import logging
import os
import time
from dataclasses import asdict, dataclass, field
from typing import Any

import requests
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_not_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from minisweagent.models import GLOBAL_MODEL_STATS

logger = logging.getLogger("vllm_model")


class VLLMConnectionError(Exception):
    """vLLM server is unreachable."""


class VLLMAPIError(Exception):
    """vLLM server returned an error."""


@dataclass
class VLLMModelConfig:
    model_name: str
    api_base: str = os.getenv("VLLM_API_BASE", "http://localhost:8000/v1")
    api_key: str = os.getenv("VLLM_API_KEY", "EMPTY")
    model_kwargs: dict[str, Any] = field(default_factory=dict)
    cost_per_million_input_tokens: float = 0.0
    cost_per_million_output_tokens: float = 0.0
    """Set non-zero values to track estimated cost for open-weight models."""
    timeout: int = int(os.getenv("VLLM_TIMEOUT", "120"))
    """HTTP request timeout in seconds."""


class VLLMModel:
    """Model class that calls a vLLM OpenAI-compatible API server.

    Implements the minisweagent Model protocol (config, cost, n_calls, query, get_template_vars).
    """

    def __init__(self, **kwargs):
        self.config = VLLMModelConfig(**kwargs)
        self.cost = 0.0
        self.n_calls = 0

        # Normalize api_base — strip trailing slash
        self.config.api_base = self.config.api_base.rstrip("/")

        if os.getenv("VLLM_DEBUG") == "true":
            logger.setLevel(logging.DEBUG)

    @retry(
        stop=stop_after_attempt(int(os.getenv("MSWEA_MODEL_RETRY_STOP_AFTER_ATTEMPT", "10"))),
        wait=wait_exponential(multiplier=1, min=4, max=60),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        retry=retry_if_not_exception_type(
            (
                VLLMConnectionError,
                KeyboardInterrupt,
            )
        ),
    )
    def _query(self, messages: list[dict[str, str]], **kwargs) -> dict:
        url = f"{self.config.api_base}/chat/completions"
        headers = {
            "Content-Type": "application/json",
        }
        if self.config.api_key and self.config.api_key != "EMPTY":
            headers["Authorization"] = f"Bearer {self.config.api_key}"

        payload = {
            "model": self.config.model_name,
            "messages": messages,
            **(self.config.model_kwargs | kwargs),
        }

        logger.debug(f"POST {url} model={self.config.model_name}")

        try:
            response = requests.post(
                url, headers=headers, json=payload, timeout=self.config.timeout
            )
        except requests.exceptions.ConnectionError as e:
            raise VLLMConnectionError(
                f"Cannot connect to vLLM server at {self.config.api_base}. "
                f"Make sure the server is running. Error: {e}"
            ) from e
        except requests.exceptions.Timeout as e:
            raise VLLMAPIError(
                f"vLLM request timed out after {self.config.timeout}s"
            ) from e

        if response.status_code != 200:
            raise VLLMAPIError(
                f"vLLM returned HTTP {response.status_code}: {response.text}"
            )

        return response.json()

    def _estimate_cost(self, usage: dict) -> float:
        """Estimate cost based on configured per-token pricing."""
        prompt_tokens = usage.get("prompt_tokens", 0)
        completion_tokens = usage.get("completion_tokens", 0)
        input_cost = (prompt_tokens / 1_000_000) * self.config.cost_per_million_input_tokens
        output_cost = (completion_tokens / 1_000_000) * self.config.cost_per_million_output_tokens
        return input_cost + output_cost

    def query(self, messages: list[dict[str, str]], **kwargs) -> dict:
        response = self._query(messages, **kwargs)

        usage = response.get("usage", {})
        cost = self._estimate_cost(usage)

        self.n_calls += 1
        self.cost += cost
        GLOBAL_MODEL_STATS.add(cost)

        content = response["choices"][0]["message"]["content"] or ""

        return {
            "content": content,
            "extra": {
                "response": response,
                "usage": usage,
                "cost": cost,
            },
        }

    def get_template_vars(self) -> dict[str, Any]:
        return asdict(self.config) | {"n_model_calls": self.n_calls, "model_cost": self.cost}
