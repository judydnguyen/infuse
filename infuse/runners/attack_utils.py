"""
Attack loading and creation utilities.

This module provides common functions for loading attack payloads and
creating Attack objects from configuration dictionaries.
"""

import json
import sys
from pathlib import Path
from typing import Dict, Any, Optional, List

# Import attack classes
try:
    from infuse.attacks.base_attack import Attack, SingleSurfaceInjection, MultiSurfacePersistentInjection
    from infuse.tasks.task_suite import SurfaceType
    ATTACK_SYSTEM_AVAILABLE = True
except ImportError:
    ATTACK_SYSTEM_AVAILABLE = False
    Attack = None
    SingleSurfaceInjection = None
    MultiSurfacePersistentInjection = None
    SurfaceType = None


def get_attack_templates_paths() -> List[Path]:
    """
    Get list of paths where attack templates may be found.

    Returns:
        List of Path objects for attack template files
    """
    from infuse.paths import REPO_ROOT
    base_dir = REPO_ROOT
    return [
        base_dir / "data" / "ATTACK_TEMPLATES.json",
        base_dir / "tasks" / "task_prompts" / "attack_template.json",
    ]


def load_attack_payload(attack_id: int) -> str:
    """
    Load attack payload from ATTACK_TEMPLATES.json by ID.

    Searches multiple possible locations for the template file.

    Args:
        attack_id: Attack ID (integer)

    Returns:
        Payload string from prompt_example, or empty string if not found
    """
    for path in get_attack_templates_paths():
        if not path.exists():
            continue

        try:
            with open(path, "r") as f:
                templates = json.load(f)

            for atk in templates:
                if atk.get("id") == attack_id:
                    return atk.get("prompt_example", "")
        except Exception:
            continue

    return ""


def load_attack_template(attack_id: int) -> Optional[Dict[str, Any]]:
    """
    Load full attack template by ID.

    Args:
        attack_id: Attack ID (integer)

    Returns:
        Attack template dictionary, or None if not found
    """
    for path in get_attack_templates_paths():
        if not path.exists():
            continue

        try:
            with open(path, "r") as f:
                templates = json.load(f)

            for atk in templates:
                if atk.get("id") == attack_id:
                    return atk
        except Exception:
            continue

    return None


def create_attack_from_config(attack_config: Dict[str, Any]) -> Optional[Attack]:
    """
    Create an Attack instance from configuration dictionary.

    Supports:
    - Single surface injection: {"type": "single", "surface": "FILE_READ", "payload": "..."}
    - Multi surface injection: {"type": "multi", "surfaces": [...], "payloads": [...]}
    - Multiple surfaces with single type: {"type": "single", "surfaces": [...], "payload": "..."}

    Args:
        attack_config: Attack configuration dictionary with:
            - type: "single" or "multi"
            - surface/surfaces: Surface type(s) to target
            - payload/payloads: Attack payload(s)
            - attack_id: Identifier for the attack

    Returns:
        Attack object, or None if creation fails
    """
    if not ATTACK_SYSTEM_AVAILABLE:
        print("Warning: Attack system not available", file=sys.stderr)
        return None

    if not attack_config:
        return None

    # Handle nested TOML format: {"attack": {"id": ..., "surfaces": {"primary": [...]}, "payload": {"template": ...}}}
    nested = attack_config.get("attack", {})
    if nested and not attack_config.get("surfaces") and not attack_config.get("surface"):
        nested_surfaces = nested.get("surfaces", {})
        nested_payload = nested.get("payload", {})
        attack_config = {
            "type": "single",
            "attack_id": str(nested.get("id", "unknown")),
            "surfaces": nested_surfaces.get("primary", []) if isinstance(nested_surfaces, dict) else nested_surfaces,
            "payload": nested_payload.get("template", "") if isinstance(nested_payload, dict) else str(nested_payload or ""),
        }

    attack_type = attack_config.get("type", "single")
    attack_id = attack_config.get("attack_id", "attack_1")

    # Get surfaces - support both "surface" (single) and "surfaces" (list)
    surfaces_str = attack_config.get("surfaces") or ([attack_config.get("surface")] if attack_config.get("surface") else [])

    # Convert to valid SurfaceType enums, skipping unknowns
    valid_surface_names = {s.value for s in SurfaceType}
    surfaces = [SurfaceType(s) for s in surfaces_str if s and s in valid_surface_names]

    if not surfaces:
        print(f"Warning: No valid surfaces in {surfaces_str}", file=sys.stderr)
        return None

    # Get payload
    payload = attack_config.get("payload") or ""
    if not payload:
        try:
            aid = attack_id
            if isinstance(aid, str) and aid.startswith("attack_"):
                aid = int(aid.replace("attack_", ""))
            elif isinstance(aid, str) and aid.isdigit():
                aid = int(aid)
            payload = load_attack_payload(aid) if isinstance(aid, int) else ""
        except (ValueError, TypeError):
            payload = ""

    if attack_type == "multi":
        payloads = attack_config.get("payloads") or [payload] * len(surfaces)
        return MultiSurfacePersistentInjection(attack_id, surfaces, payloads)

    if len(surfaces) == 1:
        return SingleSurfaceInjection(attack_id, surfaces[0], payload)
    return SingleSurfaceInjection(attack_id, surfaces, payload)


def create_attack_config_from_template(
    attack_id: int,
    task=None,
    attack_type: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """
    Create attack configuration from template file.

    Args:
        attack_id: Attack ID from ATTACK_TEMPLATES.json
        task: Optional Task object to determine target surfaces
        attack_type: Override attack type ("single" or "multi")

    Returns:
        Attack configuration dictionary, or None if template not found
    """
    if not ATTACK_SYSTEM_AVAILABLE:
        return None

    template = load_attack_template(attack_id)
    if not template:
        print(f"Warning: Attack template {attack_id} not found", file=sys.stderr)
        return None

    payload = template.get("prompt_example", "")
    attack_id_str = f"attack_{attack_id}"

    # Determine target surfaces
    target_surfaces = [SurfaceType.TERMINAL_OUTPUT]  # Default

    if task:
        try:
            expected = task.expected_surfaces_set()
            if expected:
                target_surfaces = list(expected)
        except Exception:
            pass

    # Determine attack type
    if attack_type is None:
        attack_type = "single" if len(target_surfaces) == 1 else "multi"

    if attack_type == "single":
        return {
            "type": "single",
            "surface": target_surfaces[0].value,
            "payload": payload,
            "attack_id": attack_id_str,
        }
    else:
        return {
            "type": "multi",
            "surfaces": [s.value for s in target_surfaces],
            "payloads": [payload] * len(target_surfaces),
            "attack_id": attack_id_str,
        }


def create_attack_injection_config(attack: Attack) -> Dict[str, Any]:
    """
    Create legacy attack_injection_config from Attack object.

    This is used for backward compatibility with run_task().

    Args:
        attack: Attack object

    Returns:
        Legacy attack injection config dictionary
    """
    if not attack:
        return {}

    return {
        "inject_attack": True,
        "attack_id": attack.attack_id,
        "attack_surfaces": [s.value for s in attack.target_surfaces],
    }
