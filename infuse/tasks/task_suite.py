"""
Task Suite - Core definitions for tasks, surfaces, and execution traces.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Dict, Any, Protocol
from pathlib import Path
import json


class SurfaceType(Enum):
    """Types of surfaces that agents can interact with."""
    FILE_READ = "FILE_READ"
    FILE_WRITE = "FILE_WRITE"
    TERMINAL_OUTPUT = "TERMINAL_OUTPUT"
    FILE_CONTENT = "FILE_CONTENT"
    # TERMINAL_INPUT = "TERMINAL_INPUT"
    METADATA_READ = "METADATA_READ"
    LOG_READ = "LOG_READ"
    NETWORK_ATTEMPT = "NETWORK_ATTEMPT"
    CONFIG_READ = "CONFIG_READ"
    CONFIG_WRITE = "CONFIG_WRITE"
    REPO_READ = "REPO_READ"
    REPO_WRITE = "REPO_WRITE"
    ERROR_MESSAGE = "ERROR_MESSAGE"
    GENERATED_ARTIFACT_READ = "GENERATED_ARTIFACT_READ"
    DOCKER_BUILD = "DOCKER_BUILD"
    DOCKER_RUN = "DOCKER_RUN"


@dataclass
class SurfaceEvent:
    """Represents an event where an agent interacts with a surface."""
    surface: SurfaceType
    content: str
    path: Optional[str] = None
    step: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ExecutionTrace:
    """Represents the execution trace of an agent running a task."""
    task_id: str
    events: List[SurfaceEvent] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    attacked_objects: List[Dict[str, Any]] = field(default_factory=list)  # Track attacked objects
    
    def add_event(self, event: SurfaceEvent):
        """Add an event to the trace."""
        self.events.append(event)
    
    def record_attacked_object(self, object_id: Optional[str], surface: Optional[SurfaceType], step: int, attack_id: str):
        """
        Record that an object has been attacked.
        
        Args:
            object_id: Unique identifier for the attacked object (e.g., "file:/path/to/file.txt")
                       Can be None for surfaces without specific objects (e.g., TERMINAL_OUTPUT)
            surface: Surface type that was attacked (can be None, will be stored as "unknown")
            step: Step number when the attack occurred
            attack_id: ID of the attack that was injected
        """
        self.attacked_objects.append({
            "object_id": object_id or f"unknown_{len(self.attacked_objects)}",  # Ensure object_id is never None
            "surface": surface.value if surface else "unknown",
            "step": step,
            "attack_id": attack_id,
            "timestamp": len(self.attacked_objects)  # Sequential index as timestamp
        })
    
    def get_attacked_objects(self) -> List[Dict[str, Any]]:
        """Get list of all attacked objects."""
        return self.attacked_objects.copy()
    
    def get_touched_objects(self) -> List[Dict[str, Any]]:
        """
        Get list of all unique objects that have been touched (read or written).
        
        Extracts object IDs from all surface events, including both READ and WRITE operations.
        This provides a comprehensive view of all objects the agent has interacted with.
        
        Returns:
            List of dictionaries with object_id, surface, step, and first_touch info
        """
        from infuse.envs.surface_detector import get_object_id
        
        touched = {}  # object_id -> info dict
        
        for event in self.events:
            # Extract object_id from event
            object_id = None
            if event.path:
                # Use path to construct object_id
                if event.surface == SurfaceType.FILE_READ or event.surface == SurfaceType.FILE_WRITE:
                    object_id = f"file:{event.path}"
                elif event.surface == SurfaceType.CONFIG_READ or event.surface == SurfaceType.CONFIG_WRITE:
                    object_id = f"config:{event.path}"
                elif event.surface == SurfaceType.REPO_READ or event.surface == SurfaceType.REPO_WRITE:
                    object_id = f"repo:{event.path}"
                elif event.surface == SurfaceType.METADATA_READ:
                    object_id = f"metadata:{event.path}"
                elif event.surface == SurfaceType.LOG_READ:
                    object_id = f"log:{event.path}"
                else:
                    object_id = event.path
            elif event.content:
                # Try to extract object_id from content/action
                object_id = get_object_id(event.content, event.surface, None)
            
            # Check metadata for object_id from output parsing
            if not object_id and event.metadata and "object_id" in event.metadata:
                object_id = event.metadata["object_id"]
            
            # Determine source type (sink for WRITE, taint for READ)
            source = None
            if event.surface in {
                SurfaceType.FILE_WRITE,
                SurfaceType.CONFIG_WRITE,
                SurfaceType.REPO_WRITE,
            }:
                source = "sink"  # WRITE operations are sinks
            elif event.surface in {
                SurfaceType.FILE_READ,
                SurfaceType.REPO_READ,
                SurfaceType.CONFIG_READ,
                SurfaceType.METADATA_READ,
                SurfaceType.LOG_READ,
                SurfaceType.GENERATED_ARTIFACT_READ,
            }:
                source = "taint"  # READ operations are taint sources
            
            if event.metadata and "source" in event.metadata:
                source = event.metadata["source"]
            
            if object_id:
                # Track first touch and all surfaces this object was touched on
                if object_id not in touched:
                    touched[object_id] = {
                        "object_id": object_id,
                        "surface": event.surface.value,
                        "first_step": event.step,
                        "surfaces": [event.surface.value],
                        "touch_count": 1,
                        "source": source or "unknown",  # sink or taint
                        "path": event.path,
                    }
                else:
                    # Object already touched - update info
                    touched[object_id]["touch_count"] += 1
                    if event.surface.value not in touched[object_id]["surfaces"]:
                        touched[object_id]["surfaces"].append(event.surface.value)
                    # Keep earliest step
                    if event.step < touched[object_id]["first_step"]:
                        touched[object_id]["first_step"] = event.step
                    # Update source if we have new information
                    if source and touched[object_id]["source"] == "unknown":
                        touched[object_id]["source"] = source
                    elif source and source != touched[object_id]["source"]:
                        # Object touched from both sink and taint
                        touched[object_id]["source"] = "both"
        
        return list(touched.values())
    
    def get_events_by_surface(self, surface: SurfaceType) -> List[SurfaceEvent]:
        """Get all events for a specific surface type."""
        return [e for e in self.events if e.surface == surface]
    
    def get_last_event(self) -> Optional[SurfaceEvent]:
        """Get the most recent event."""
        return self.events[-1] if self.events else None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert trace to dictionary for serialization."""
        return {
            "task_id": self.task_id,
            "events": [
                {
                    "surface": e.surface.value,
                    "content": e.content,
                    "path": e.path,
                    "step": e.step,
                    "metadata": e.metadata
                }
                for e in self.events
            ],
            "metadata": self.metadata,
            "attacked_objects": self.attacked_objects,
            "touched_objects": self.get_touched_objects(),
            "attack_summary": {
                "total_attacks": len(self.attacked_objects),
                "unique_objects": len(set(obj["object_id"] for obj in self.attacked_objects if obj["object_id"])),
                "surfaces_attacked": list(set(obj["surface"] for obj in self.attacked_objects))
            },
            "touch_summary": {
                "total_touched": len(self.get_touched_objects()),
                "unique_objects": len(set(obj["object_id"] for obj in self.get_touched_objects() if obj.get("object_id"))),
                "surfaces_touched": list(set(s for obj in self.get_touched_objects() for s in obj.get("surfaces", [])))
            }
        }


class TaskEnv(Protocol):
    """Protocol for task environment setup."""
    def setup_task(self, task_id: str, task_data: Dict[str, Any]) -> None:
        """Set up the environment for a task."""
        ...


class Task(ABC):
    """A task to be executed by the agent."""
    
    def __init__(self, task_id: str, category: str, user_goal: str, 
                 prompt_example: str, script_test: str, groundtruth_goal: str,
                 expected_surfaces: List[str]):
        self.task_id = task_id
        self.category = category
        self.user_goal = user_goal
        self.prompt_example = prompt_example
        self.script_test = script_test
        self.groundtruth_goal = groundtruth_goal
        self.expected_surfaces = expected_surfaces

    @abstractmethod
    def setup(self, env: TaskEnv) -> None:
        """Populate files, archives, metadata, etc."""
        pass

    def expected_surfaces_set(self) -> set[SurfaceType]:
        """Surfaces the benign agent is expected to touch."""
        result = set()
        # Filter out TERMINAL_INPUT explicitly since it's not a valid surface type
        # TERMINAL_INPUT is not a valid surface - agents propose actions, they don't interact with terminal input
        for surface_str in self.expected_surfaces:
            # Skip TERMINAL_INPUT explicitly
            if surface_str == "TERMINAL_INPUT":
                continue
            try:
                result.add(SurfaceType(surface_str))
            except (ValueError, AttributeError):
                # Skip unknown surface types (ValueError from enum, AttributeError if accessed as attribute)
                pass
        return result

    @abstractmethod
    def success_criteria(self, trace: ExecutionTrace) -> bool:
        """Check if the task was completed successfully."""
        pass
    
    def get_prompt(self) -> str:
        """Get the prompt to give to the agent."""
        return self.prompt_example
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert task to dictionary format."""
        return {
            "id": self.task_id,  # Include "id" for compatibility with trajectory format
            "task_id": self.task_id,
            "task_category": self.category,
            "user_goal": self.user_goal,
            "prompt_example": self.prompt_example,
            "script_test": self.script_test,
            "groundtruth_goal": self.groundtruth_goal,
            "expected_surfaces": self.expected_surfaces
        }


class BenignTask(Task):
    """A benign task loaded from BENIGN_TASKS.json."""
    
    def __init__(self, task_data: Dict[str, Any]):
        super().__init__(
            task_id=str(task_data.get("task_id", "")),
            category=task_data.get("task_category", ""),
            user_goal=task_data.get("user_goal", ""),
            prompt_example=task_data.get("prompt_example", ""),
            script_test=task_data.get("script_test", ""),
            groundtruth_goal=task_data.get("groundtruth_goal", ""),
            expected_surfaces=task_data.get("expected_surfaces", [])
        )
    
    def setup(self, env: TaskEnv) -> None:
        """Setup is handled by the environment based on task_id."""
        # The environment should set up files based on task_id
        # For example, my_pc/task{task_id}/ should contain the necessary files
        pass
    
    def success_criteria(self, trace: ExecutionTrace) -> bool:
        """
        Check if task was successful based on the script_test description.
        This is a simplified check - in practice, you'd run the actual test script.
        """
        # Basic heuristic: check if expected surfaces were touched
        expected = self.expected_surfaces_set()
        actual = {event.surface for event in trace.events}
        
        # At minimum, some expected surfaces should be touched
        if expected and not (expected & actual):
            return False
        
        # Additional checks could be added here based on script_test
        # For now, we'll return True if expected surfaces were touched
        return True


def load_benign_tasks(json_path: Optional[str] = None) -> List[BenignTask]:
    """
    Load benign tasks from BENIGN_TASKS.json.
    
    Args:
        json_path: Path to BENIGN_TASKS.json. If None, uses default location.
        
    Returns:
        List of BenignTask objects.
    """
    if json_path is None:
        from infuse.paths import TEMPLATES_DIR
        json_path = TEMPLATES_DIR / "BENIGN_TASKS.json"
    
    with open(json_path, 'r') as f:
        tasks_data = json.load(f)
    
    return [BenignTask(task_data) for task_data in tasks_data]


def get_task_by_id(task_id: int, json_path: Optional[str] = None, task_dir: Optional[str] = None) -> Optional[BenignTask]:
    """
    Get a specific task by ID.
    
    Args:
        task_id: The task ID to retrieve.
        json_path: Path to BENIGN_TASKS.json. If None, uses default location.
        
    Returns:
        BenignTask object if found, None otherwise.
    """
    tasks = load_benign_tasks(json_path)
    for task in tasks:
        if task.task_id == str(task_id):
            return task
    return None
