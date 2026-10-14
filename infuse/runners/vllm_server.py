"""Launch a vLLM OpenAI-compatible server for a model key from ``benchmark/configs/models.yaml``."""
from __future__ import annotations

import os
import subprocess
import sys

from infuse import paths
from infuse.registry.models import load_models


def build_command(model_key: str, port: int | None = None) -> list[str]:
    models = load_models()
    if model_key not in models:
        raise KeyError(f"{model_key!r} not in {paths.MODELS_YAML}; known: {sorted(models)}")
    cfg = models[model_key]
    cmd = [sys.executable, "-m", "vllm.entrypoints.openai.api_server",
           "--model", cfg["model_id"],
           "--tensor-parallel-size", str(cfg.get("tensor_parallel_size", 1)),
           "--port", str(port or cfg.get("port", 8000)),
           "--max-model-len", str(cfg.get("max_model_len", 8192)),
           "--dtype", str(cfg.get("dtype", "auto")),
           "--trust-remote-code"]
    if cfg.get("gpu_memory_utilization"):
        cmd += ["--gpu-memory-utilization", str(cfg["gpu_memory_utilization"])]
    if cfg.get("revision"):
        cmd += ["--revision", cfg["revision"]]
    return cmd


def serve(model_key: str, port: int | None = None, dry_run: bool = False) -> int:
    os.environ.setdefault("HF_HUB_OFFLINE", "0")
    os.environ.setdefault("HUGGINGFACE_HUB_CACHE", str(paths.HF_CACHE))
    cmd = build_command(model_key, port)
    print("Launching:", " ".join(cmd), file=sys.stderr)
    if dry_run:
        return 0
    return subprocess.run(cmd).returncode


__all__ = ["build_command", "serve"]
