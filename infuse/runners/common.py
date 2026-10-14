"""
Common utilities for task runners.

This module consolidates shared functionality used across multiple runners:
- Model name normalization
- Default configuration loading
- Docker configuration setup
"""

import os
import sys
from pathlib import Path
from typing import Dict, Any, Optional

# Model name aliases for normalization
MODEL_ALIASES: Dict[str, str] = {
    "gpt-3.5": "gpt-3.5-turbo",
    "gpt-3": "gpt-3.5-turbo",
    "gpt3": "gpt-3.5-turbo",
    "gpt4": "gpt-4",
    "gpt-4o": "gpt-4o",
    "gpt-4-turbo": "gpt-4-turbo-preview",
    "claude": "claude-3-opus-20240229",
    "claude-3": "claude-3-opus-20240229",
    "claude-3-opus": "claude-3-opus-20240229",
}


def normalize_model_name(model_name: str, warn: bool = True) -> str:
    """
    Normalize model name for LiteLLM compatibility.

    Args:
        model_name: Input model name (e.g., "gpt4", "claude-3")
        warn: Whether to print warning when normalizing

    Returns:
        Normalized model name suitable for LiteLLM
    """
    original = model_name
    lower = model_name.lower()

    # Check exact match first
    if lower in MODEL_ALIASES:
        normalized = MODEL_ALIASES[lower]
        if warn and normalized != original:
            print(f"⚠ Normalized model name: {original} → {normalized}", file=sys.stderr)
        return normalized

    # Check partial matches
    if "gpt-3.5" in lower and "turbo" not in lower:
        if warn:
            print(f"⚠ Normalized model name: {original} → gpt-3.5-turbo", file=sys.stderr)
        return "gpt-3.5-turbo"

    return model_name


def load_default_config() -> Dict[str, Any]:
    """
    Load default agent configuration from YAML.

    Looks for config at agents/minisweagent/config/default.yaml

    Returns:
        Configuration dictionary with 'agent' and 'environment' keys,
        or empty dict if config not found
    """
    import yaml

    from infuse.paths import AGENT_DEFAULT_CONFIG
    config_path = AGENT_DEFAULT_CONFIG
    if config_path.exists():
        with open(config_path) as f:
            return yaml.safe_load(f) or {}
    return {}


def setup_docker_config(
    env_config: Optional[Dict[str, Any]] = None,
    docker_image: str = "agent-bench-base:latest",
    docker_cwd: str = "/work",
    docker_volumes: Optional[list] = None,
    docker_run_args: Optional[list] = None,
    data_in_image: bool = False,
) -> Dict[str, Any]:
    """
    Create Docker environment configuration.

    Args:
        env_config: Base environment config (timeout, env vars, etc.)
        docker_image: Docker image name
        docker_cwd: Working directory in container
        docker_volumes: Volume mounts (host:container:ro format)
        docker_run_args: Additional docker run arguments
        data_in_image: If True, data is in image at /app

    Returns:
        Complete Docker environment configuration dict
    """
    env_config = env_config or {}

    if data_in_image:
        # Data already in Docker image at /app
        effective_cwd = "/app"
        run_args = docker_run_args or [
            "--rm",
            "--tmpfs", "/tmp:rw,noexec,nosuid,size=100m,mode=1777",
        ]
        effective_volumes = docker_volumes or []
    else:
        # Legacy mode: data mounted from host
        effective_cwd = docker_cwd
        run_args = docker_run_args or [
            "--rm",
            "--tmpfs", "/work:rw,noexec,nosuid,size=1g,mode=1777",
            "--tmpfs", "/tmp:rw,noexec,nosuid,size=100m,mode=1777",
            "--read-only",
        ]
        effective_volumes = docker_volumes or []

    return {
        "environment_class": "docker",
        "image": docker_image,
        "cwd": effective_cwd,
        "run_args": run_args,
        "timeout": env_config.get("timeout", 30),
        "env": env_config.get("env", {}),
        "forward_env": env_config.get("forward_env", []),
        "volumes": effective_volumes,
    }


def setup_daytona_config(
    env_config: Optional[Dict[str, Any]] = None,
    daytona_image: Optional[str] = None,
    daytona_cwd: str = "/work",
    daytona_env: Optional[Dict[str, str]] = None,
    sync_dirs: Optional[list] = None,
) -> Dict[str, Any]:
    """
    Create Daytona sandbox environment configuration.

    Args:
        env_config: Base environment config
        daytona_image: Sandbox image (if supported)
        daytona_cwd: Working directory in sandbox
        daytona_env: Environment variables
        sync_dirs: Directories to sync (local:remote tuples)

    Returns:
        Daytona environment configuration dict
    """
    env_config = env_config or {}

    return {
        "environment_class": "daytona",
        "image": daytona_image,
        "cwd": daytona_cwd,
        "timeout": env_config.get("timeout", 30),
        "env": daytona_env or env_config.get("env", {}),
        "sync_dirs": sync_dirs or [],
    }


def get_model_config(
    model_name: Optional[str] = None,
    model_config: Optional[Dict[str, Any]] = None,
    model_class: Optional[str] = None,
) -> tuple[str, Dict[str, Any]]:
    """
    Prepare model configuration.

    Args:
        model_name: Model name (optional, falls back to env/config)
        model_config: Existing model config dict
        model_class: Model class (anthropic, litellm, openrouter)

    Returns:
        Tuple of (normalized_model_name, model_config_dict)
    """
    config = model_config.copy() if model_config else {}

    # Determine model name
    name = model_name or config.get("model_name") or os.getenv("MSWEA_MODEL_NAME", "gpt-4")
    name = normalize_model_name(name)
    config["model_name"] = name

    # Add model class if specified
    if model_class:
        config["model_class"] = model_class

    return name, config


def get_agent_config(
    agent_config: Optional[Dict[str, Any]] = None,
    cost_limit: Optional[float] = None,
    workspace_dir: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Prepare agent configuration with defaults.

    Args:
        agent_config: Custom agent config (merged with defaults)
        cost_limit: Maximum cost in USD
        workspace_dir: Agent workspace directory

    Returns:
        Complete agent configuration dict
    """
    # Load defaults
    defaults = load_default_config().get("agent", {})

    # Merge custom config with defaults
    if agent_config:
        config = {**defaults, **agent_config}
    else:
        config = defaults.copy()

    # Apply overrides
    if cost_limit is not None:
        config["cost_limit"] = cost_limit

    if workspace_dir:
        config["workspace_dir"] = workspace_dir

    return config
