import json
import logging
import os
import threading
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Literal

import litellm
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_not_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from minisweagent.models import GLOBAL_MODEL_STATS
from minisweagent.models.utils.cache_control import set_cache_control

logger = logging.getLogger("litellm_model")

# Default RPM cap for Gemini models (conservative free-tier limit)
_GEMINI_DEFAULT_RPM = int(os.getenv("GEMINI_RPM_LIMIT", "10"))


class _RateLimiter:
    """Token-bucket rate limiter: enforces a max requests-per-minute."""

    def __init__(self, rpm: int):
        self._min_interval = 60.0 / rpm
        self._lock = threading.Lock()
        self._last_call: float = 0.0

    def wait(self):
        with self._lock:
            now = time.monotonic()
            wait_for = self._min_interval - (now - self._last_call)
            if wait_for > 0:
                logger.debug(f"Rate limiter sleeping {wait_for:.2f}s to stay under RPM cap")
                time.sleep(wait_for)
            self._last_call = time.monotonic()


@dataclass
class LitellmModelConfig:
    model_name: str
    model_kwargs: dict[str, Any] = field(default_factory=dict)
    litellm_model_registry: Path | str | None = os.getenv("LITELLM_MODEL_REGISTRY_PATH")
    set_cache_control: Literal["default_end"] | None = None
    """Set explicit cache control markers, for example for Anthropic models"""
    rpm_limit: int | None = None
    """Max requests per minute. Defaults to GEMINI_RPM_LIMIT (10) for Gemini models, None otherwise."""


class LitellmModel:
    def __init__(self, *, config_class: type = LitellmModelConfig, **kwargs):
        self.config = config_class(**kwargs)
        self.cost = 0.0
        self.n_calls = 0

        # Auto-enable rate limiting for Gemini models
        rpm = self.config.rpm_limit
        if rpm is None and "gemini" in self.config.model_name.lower():
            rpm = _GEMINI_DEFAULT_RPM
        self._rate_limiter = _RateLimiter(rpm) if rpm else None
        if self._rate_limiter:
            logger.info(f"Rate limiter enabled: {rpm} RPM for model '{self.config.model_name}'")
        
        # Validate model name format
        model_name = self.config.model_name
        if "/" not in model_name and not any(
            provider in model_name.lower() 
            for provider in ["gpt", "claude", "gemini", "llama", "mistral", "cohere"]
        ):
            logger.warning(
                f"Model name '{model_name}' doesn't include a provider prefix. "
                f"Consider using format like 'anthropic/claude-3-5-sonnet' or 'openai/gpt-4'. "
                f"LiteLLM may not be able to determine the provider automatically."
            )
        
        # Enable debug logging if requested via environment variable
        if os.getenv("LITELLM_LOG") == "DEBUG" or os.getenv("LITELLM_DEBUG") == "true":
            try:
                litellm.set_verbose = True
                litellm._turn_on_message_logging()
                logger.info("LiteLLM debug logging enabled")
            except AttributeError:
                # Fallback for older litellm versions
                logger.setLevel(logging.DEBUG)
                logger.info("LiteLLM debug logging enabled (fallback mode)")
            
            # Also enable Python logging at DEBUG level
            logger.setLevel(logging.DEBUG)
            logging.getLogger("litellm").setLevel(logging.DEBUG)
        
        if self.config.litellm_model_registry and Path(self.config.litellm_model_registry).is_file():
            litellm.utils.register_model(json.loads(Path(self.config.litellm_model_registry).read_text()))

        # Auto-register model with zero cost if not in litellm's registry.
        # This prevents "This model isn't mapped yet" errors for local/self-hosted
        # models (vLLM, Ollama, TGI, etc.) that litellm has no pricing data for.
        model_key = self.config.model_name
        if model_key not in litellm.model_cost:
            provider = model_key.split("/")[0] if "/" in model_key else "openai"
            litellm.utils.register_model({
                model_key: {
                    "max_tokens": 8192,
                    "input_cost_per_token": 0.0,
                    "output_cost_per_token": 0.0,
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
                litellm.exceptions.UnsupportedParamsError,
                litellm.exceptions.NotFoundError,
                litellm.exceptions.PermissionDeniedError,
                litellm.exceptions.ContextWindowExceededError,
                litellm.exceptions.APIError,
                litellm.exceptions.AuthenticationError,
                litellm.exceptions.BadRequestError,
                KeyboardInterrupt,
            )
        ),
    )
    def _query(self, messages: list[dict[str, str]], **kwargs):
        if self._rate_limiter:
            self._rate_limiter.wait()
        try:
            # Log the model name being used for debugging
            if os.getenv("LITELLM_LOG") == "DEBUG" or os.getenv("LITELLM_DEBUG") == "true":
                logger.debug(f"Calling litellm.completion with model: {self.config.model_name}")
                logger.debug(f"Model kwargs: {self.config.model_kwargs}")
            
            return litellm.completion(
                model=self.config.model_name, messages=messages, **(self.config.model_kwargs | kwargs)
            )
        except litellm.exceptions.BadRequestError as e:
            # Provide more helpful error message for provider/model name issues
            error_msg = str(e)
            if "LLM Provider NOT provided" in error_msg or "Provider" in error_msg:
                logger.error(
                    f"Model name format error: '{self.config.model_name}'\n"
                    f"LiteLLM couldn't determine the provider. Make sure the model name includes the provider prefix.\n"
                    f"Examples: 'anthropic/claude-3-5-sonnet', 'openai/gpt-4', 'anthropic/claude-3-opus-20240229'\n"
                    f"Full error: {error_msg}"
                )
            raise e
        except litellm.exceptions.AuthenticationError as e:
            e.message += " You can permanently set your API key with `mini-extra config set KEY VALUE`."
            raise e
        except Exception as e:
            # Log any other errors with model name for debugging
            logger.error(f"Error calling litellm with model '{self.config.model_name}': {e}")
            raise e

    def query(self, messages: list[dict[str, str]], **kwargs) -> dict:
        if self.config.set_cache_control:
            messages = set_cache_control(messages, mode=self.config.set_cache_control)
        response = self._query(messages, **kwargs)
        try:
            try:
                cost = litellm.cost_calculator.completion_cost(response)
            except Exception:
                # Gateways may return dated model ids (e.g. gpt-5.4-2026-03-05)
                # that are not in litellm's price table; fall back to the
                # configured model name so the cost limit still applies.
                cost = litellm.cost_calculator.completion_cost(response, model=self.config.model_name)
        except Exception as e:
            logger.warning(
                f"Could not calculate cost for model '{self.config.model_name}': {e}. "
                "Defaulting to $0.00 (expected for local/self-hosted models). "
                "To suppress this, register the model via LITELLM_MODEL_REGISTRY_PATH."
            )
            cost = 0.0
        self.n_calls += 1
        assert cost >= 0.0, f"Cost is negative: {cost}"
        self.cost += cost
        GLOBAL_MODEL_STATS.add(cost)
        return {
            "content": response.choices[0].message.content or "",  # type: ignore
            "extra": {
                "response": response.model_dump(),
            },
        }

    def get_template_vars(self) -> dict[str, Any]:
        return asdict(self.config) | {"n_model_calls": self.n_calls, "model_cost": self.cost}
