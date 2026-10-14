"""
Task and trace utilities.

This module provides common functions for working with tasks and execution traces.
"""

from pathlib import Path
from typing import Dict, Any, Optional, Union

# Import task system
try:
    from infuse.tasks.task_suite import Task, ExecutionTrace
    TASK_SYSTEM_AVAILABLE = True
except ImportError:
    TASK_SYSTEM_AVAILABLE = False
    Task = None
    ExecutionTrace = None


def normalize_task_id(task_id: Union[int, str]) -> str:
    """
    Normalize task ID by removing 'benign_' prefix if present.

    Args:
        task_id: Task ID (can be int or string like "2", "benign_2", etc.)

    Returns:
        Normalized task ID as string (numeric part only)
    """
    if isinstance(task_id, int):
        return str(task_id)

    task_id_str = str(task_id)
    if task_id_str.startswith("benign_"):
        return task_id_str[7:]  # Remove "benign_" (7 characters)

    return task_id_str


def get_task_prompt(task_entry: Union[dict, Task]) -> str:
    """
    Extract task prompt from task entry.

    Args:
        task_entry: Task dictionary or Task object

    Returns:
        Task prompt string
    """
    if TASK_SYSTEM_AVAILABLE and isinstance(task_entry, Task):
        return task_entry.get_prompt()

    # Dict-based task
    return task_entry.get("prompt_example", task_entry.get("user_goal", ""))


def get_task_dict(task_entry: Union[dict, Task]) -> Dict[str, Any]:
    """
    Convert task entry to dictionary format.

    Args:
        task_entry: Task dictionary or Task object

    Returns:
        Task as dictionary
    """
    if TASK_SYSTEM_AVAILABLE and isinstance(task_entry, Task):
        return task_entry.to_dict()

    return task_entry


def get_task_id(task_entry: Union[dict, Task]) -> str:
    """
    Extract task ID from task entry.

    Args:
        task_entry: Task dictionary or Task object

    Returns:
        Task ID as string
    """
    if TASK_SYSTEM_AVAILABLE and isinstance(task_entry, Task):
        return str(task_entry.task_id)

    return str(task_entry.get("task_id", task_entry.get("id", "unknown")))


def extract_trace_stats(trace) -> Dict[str, Any]:
    """
    Extract statistics from execution trace.

    Args:
        trace: ExecutionTrace object or trace-like dict

    Returns:
        Dictionary with trace statistics:
        - total_events: Number of events
        - surface_counts: Dict mapping surface types to counts
    """
    if not trace:
        return {}

    stats = {}
    events = []

    # Get events from trace
    if hasattr(trace, 'events'):
        events = trace.events
    elif hasattr(trace, 'metadata'):
        events = trace.metadata.get("trace", {}).get("events", [])
    elif isinstance(trace, dict):
        events = trace.get("events", [])

    if not events:
        return stats

    stats["total_events"] = len(events)

    # Count events by surface type
    surface_counts = {}
    for event in events:
        if isinstance(event, dict):
            surface = event.get("surface", "")
        else:
            # Event object
            surface = getattr(event.surface, 'value', str(event.surface)) if hasattr(event, 'surface') else ""

        if surface:
            surface_counts[surface] = surface_counts.get(surface, 0) + 1

    if surface_counts:
        stats["surface_counts"] = surface_counts

    return stats


def create_execution_trace(
    task_entry: Union[dict, Task],
    task_type: str = "benign",
) -> Optional[ExecutionTrace]:
    """
    Create an ExecutionTrace for a task.

    Args:
        task_entry: Task dictionary or Task object
        task_type: Type of task ("benign" or "attack")

    Returns:
        ExecutionTrace object, or None if task system unavailable
    """
    if not TASK_SYSTEM_AVAILABLE or ExecutionTrace is None:
        return None

    task_id = get_task_id(task_entry)
    task_dict = get_task_dict(task_entry)

    return ExecutionTrace(
        task_id=task_id,
        metadata={
            "task_type": task_type,
            "category": task_dict.get("task_category", task_dict.get("category", "unknown")),
        }
    )


def generate_trajectory_filename(
    task_entry: Union[dict, Task],
    task_type: str,
    output_dir: Union[str, Path],
    task_index: int,
    attack_id: Optional[Union[int, str]] = None,
    seed: Optional[int] = None,
    model_name: Optional[str] = None,
    benign_task_id: Optional[Union[int, str]] = None,
) -> Path:
    """
    Generate trajectory filename with proper directory structure.

    Path structure:
    - Benign: benign_task/{model}/{task_id}/{index}_{task_id}.traj.json
    - Attack: attack_task/{attack_id}/{benign_task_id}/{model}/{index}_{task_id}.traj.json

    Args:
        task_entry: Task dictionary or Task object
        task_type: Type of task ("benign" or "attack")
        output_dir: Base output directory
        task_index: Index of task (for filename prefix)
        attack_id: Optional attack ID
        seed: Optional seed for filename
        model_name: Optional model name for path structure
        benign_task_id: Optional benign task ID (required for attacks)

    Returns:
        Path to trajectory file
    """
    output_dir = Path(output_dir)
    task_id = get_task_id(task_entry)

    # Normalize benign_task_id
    if benign_task_id:
        benign_task_id = normalize_task_id(benign_task_id)

    # Build path based on task type
    path_parts = []

    if task_type == "attack" or benign_task_id:
        # Attack task or benign task paired with attack
        path_parts.append("attack_task")
        path_parts.append(str(attack_id or "unknown"))
        path_parts.append(benign_task_id or normalize_task_id(task_id))
    else:
        # Standalone benign task
        path_parts.append("benign_task")

    # Add model name
    if model_name:
        path_parts.append(model_name.replace("/", "_").replace(":", "_"))

    # Add task_id for standalone benign tasks
    if task_type == "benign" and not benign_task_id:
        path_parts.append(str(task_id))

    output_path = output_dir.joinpath(*path_parts)

    # Build filename
    base_name = f"{task_index}_{task_id}"
    if attack_id:
        base_name += f"_attack{attack_id}"
    if seed:
        base_name += f"_seed{seed}"

    return output_path / f"{base_name}.traj.json"


def get_workdir_from_env(env) -> str:
    """
    Get working directory from environment object.

    Args:
        env: Environment object (may be wrapped)

    Returns:
        Working directory path as string
    """
    if hasattr(env, 'cwd'):
        return env.cwd
    elif hasattr(env, 'base_env') and hasattr(env.base_env, 'cwd'):
        return env.base_env.cwd

    return str(Path.cwd())
