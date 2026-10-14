import dataclasses
import json
import re
from collections.abc import Callable
from pathlib import Path
from typing import Any

from minisweagent import Agent, __version__


def _get_class_name_with_module(obj: Any) -> str:
    """Get the full class name with module path."""
    return f"{obj.__class__.__module__}.{obj.__class__.__name__}"


def _asdict(obj: Any) -> dict:
    """Convert config objects to dicts."""
    if dataclasses.is_dataclass(obj):
        return dataclasses.asdict(obj)  # type: ignore[arg-type]
    return obj  # let's try our luck


def _extract_action_from_content(content: str) -> str | None:
    """Extract bash action from message content."""
    if not content:
        return None
    # Match bash code blocks: ```bash\n...\n```
    match = re.search(r"```bash\n(.*?)\n```", content, re.DOTALL)
    if match:
        return match.group(1).strip()
    return None


def _add_action_to_message(message: dict) -> dict:
    """Add extracted action field to message structure."""
    # Create a deep copy to avoid modifying the original
    msg = json.loads(json.dumps(message))
    
    # Extract action from main content
    content = msg.get("content", "")
    action = _extract_action_from_content(content)
    
    # Add action to the message itself
    if action:
        msg["action"] = action
    
    # Also add to extra.response.choices[0].message if it exists
    if "extra" in msg and isinstance(msg["extra"], dict):
        extra = msg["extra"]
        if "response" in extra and isinstance(extra["response"], dict):
            response = extra["response"]
            if "choices" in response and isinstance(response["choices"], list) and len(response["choices"]) > 0:
                choice = response["choices"][0]
                if "message" in choice and isinstance(choice["message"], dict):
                    choice["message"]["action"] = action
    
    return msg


def _redact_model_config(cfg):
    """Strip credentials (gateway headers / api keys) before they are written to disk."""
    if isinstance(cfg, dict) and isinstance(cfg.get("model_kwargs"), dict):
        kw = {k: v for k, v in cfg["model_kwargs"].items() if k not in ("api_key", "extra_headers")}
        cfg = {**cfg, "model_kwargs": kw}
    return cfg


def save_traj(
    agent: Agent | None,
    path: Path,
    *,
    print_path: bool = True,
    exit_status: str | None = None,
    result: str | None = None,
    extra_info: dict | None = None,
    print_fct: Callable = print,
    **kwargs,
):
    """Save the trajectory of the agent to a file.

    Args:
        agent: The agent to save the trajectory of.
        path: The path to save the trajectory to.
        print_path: Whether to print confirmation of path to the terminal.
        exit_status: The exit status of the agent.
        result: The result/submission of the agent.
        extra_info: Extra information to save (will be merged into the info dict).
        **kwargs: Additional information to save (will be merged into top level)

    """
    data = {
        "info": {
            "exit_status": exit_status,
            "submission": result,
            "model_stats": {
                "instance_cost": 0.0,
                "api_calls": 0,
            },
            "mini_version": __version__,
        },
        "messages": [],
        "trajectory_format": "mini-swe-agent-1",
    } | kwargs
    if agent is not None:
        data["info"]["model_stats"]["instance_cost"] = agent.model.cost
        data["info"]["model_stats"]["api_calls"] = agent.model.n_calls
        # Process messages to extract and add actions
        data["messages"] = [_add_action_to_message(msg) for msg in agent.messages]
        data["info"]["config"] = {
            "agent": _asdict(agent.config),
            "model": _redact_model_config(_asdict(agent.model.config)),
            "environment": _asdict(agent.env.config),
            "agent_type": _get_class_name_with_module(agent),
            "model_type": _get_class_name_with_module(agent.model),
            "environment_type": _get_class_name_with_module(agent.env),
        }
    if extra_info:
        data["info"].update(extra_info)

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2))
    if print_path:
        print_fct(f"Saved trajectory to '{path}'")
