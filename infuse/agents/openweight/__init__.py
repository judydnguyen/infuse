"""Open-weight model implementations for INFUSE.

Provides model classes for serving open-weight LLMs (LLaMA, Qwen, Mistral, etc.)
via vLLM (self-hosted) or LiteLLM (unified API).

Usage:
    # vLLM (self-hosted server)
    model = VLLMModel(model_name="meta-llama/Llama-3.1-70B-Instruct", api_base="http://localhost:8000/v1")

    # LiteLLM routing to local/remote open-weight endpoints
    model = LiteLLMOpenWeightModel(model_name="huggingface/meta-llama/Llama-3.1-70B-Instruct")
"""

from infuse.agents.openweight.vllm_model import VLLMModel, VLLMModelConfig
from infuse.agents.openweight.litellm_openweight_model import (
    LiteLLMOpenWeightModel,
    LiteLLMOpenWeightModelConfig,
)

__all__ = [
    "VLLMModel",
    "VLLMModelConfig",
    "LiteLLMOpenWeightModel",
    "LiteLLMOpenWeightModelConfig",
]
