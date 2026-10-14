"""
Task and Attack Configuration Models.

This module provides dataclasses for the new TOML-based task configuration system.
It supports paired benign vs malicious runs with overlay-based attack injection.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, List, Dict, Any
from enum import Enum
import json

# Optional toml support - fall back to tomllib in Python 3.11+
try:
    import toml
except ImportError:
    try:
        import tomllib as toml  # Python 3.11+
    except ImportError:
        toml = None


class AttackMethod(Enum):
    """Methods for injecting attacks into the environment."""
    FILE_INJECTION = "file_injection"       # Inject payload into file content
    CONTENT_APPEND = "content_append"       # Append payload to file content
    METADATA_MODIFY = "metadata_modify"     # Modify file metadata
    EXTERNAL_REDIRECT = "external_redirect" # Redirect external content
    RUNTIME_INJECTION = "runtime_injection" # Inject at runtime via SurfaceTrackingWrapper


class AttackSurface(Enum):
    """Attack surface types for injection targeting."""
    FILE_CONTENT = "FILE_CONTENT"           # Inject into file content
    FILE_METADATA = "FILE_METADATA"         # Modify file metadata (permissions, timestamps)
    FILENAME = "FILENAME"                   # Malicious filename patterns
    EXTERNAL_CONTENT = "EXTERNAL_CONTENT"   # External URL/API responses
    TERMINAL_OUTPUT = "TERMINAL_OUTPUT"     # Command output injection
    CONFIG_FILE = "CONFIG_FILE"             # Config file modification
    ENV_VARIABLE = "ENV_VARIABLE"           # Environment variable injection


@dataclass
class AttackConfig:
    """Configuration for an attack overlay.

    This class defines how an attack should be injected into a task environment.
    It supports both file-level injection (before task runs) and runtime injection
    (during task execution via SurfaceTrackingWrapper).

    Attributes:
        id: Unique attack identifier
        name: Human-readable attack name
        description: Detailed description of the attack
        method: How the attack should be injected (file_injection, runtime_injection, etc.)
        surfaces: List of attack surfaces to target
        fallback_surfaces: Alternative surfaces if primary surfaces aren't available
        payload_template: The attack payload template
        payload_style: Formatting style (stealthy, direct, contextual)
        target_patterns: File patterns to target for file-based injection
        inject_position: Where to inject in files (prepend, append, inline, replace)
        inject_prefix: Optional prefix to prepend to payload when injecting (e.g., "Task complete, your new task is")
        success_signals: Regex patterns that indicate attack success
    """
    id: str
    name: str
    description: str = ""
    method: AttackMethod = AttackMethod.RUNTIME_INJECTION
    surfaces: List[str] = field(default_factory=list)
    fallback_surfaces: List[str] = field(default_factory=list)
    payload_template: str = ""
    payload_style: str = "contextual"
    target_patterns: List[str] = field(default_factory=list)
    inject_position: str = "append"
    inject_prefix: str = ""
    success_signals: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_toml(cls, path: Path) -> "AttackConfig":
        """Load attack configuration from a TOML file.

        Args:
            path: Path to the attack TOML file

        Returns:
            AttackConfig instance

        Raises:
            ImportError: If toml library is not available
            FileNotFoundError: If the file doesn't exist
        """
        if toml is None:
            raise ImportError("toml library required. Install with: pip install toml")

        if hasattr(toml, 'load'):
            with open(path, 'r') as f:
                data = toml.load(f)
        else:
            # tomllib requires binary mode
            with open(path, 'rb') as f:
                data = toml.load(f)

        attack = data.get("attack", {})
        method_data = attack.get("method", {})
        surfaces_data = attack.get("surfaces", {})
        payload_data = attack.get("payload", {})
        target_data = attack.get("target", {})
        success_data = attack.get("success_criteria", {})

        # Parse method type
        method_str = method_data.get("type", "runtime_injection")
        try:
            method = AttackMethod(method_str)
        except ValueError:
            method = AttackMethod.RUNTIME_INJECTION

        return cls(
            id=str(attack.get("id", "")),
            name=attack.get("name", ""),
            description=attack.get("description", ""),
            method=method,
            surfaces=surfaces_data.get("primary", []),
            fallback_surfaces=surfaces_data.get("fallback", []),
            payload_template=payload_data.get("template", ""),
            payload_style=payload_data.get("style", "contextual"),
            target_patterns=target_data.get("file_patterns", []),
            inject_position=target_data.get("inject_position", "append"),
            inject_prefix=target_data.get("inject_prefix", ""),
            success_signals=success_data.get("signals", []),
            metadata=attack.get("metadata", {}),
        )

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AttackConfig":
        """Create AttackConfig from a dictionary.

        Args:
            data: Dictionary with attack configuration

        Returns:
            AttackConfig instance
        """
        attack = data.get("attack", data)  # Support both nested and flat formats
        method_data = attack.get("method", {})
        surfaces_data = attack.get("surfaces", {})
        payload_data = attack.get("payload", {})
        target_data = attack.get("target", {})
        success_data = attack.get("success_criteria", {})

        # Parse method type
        method_str = method_data.get("type", "runtime_injection") if isinstance(method_data, dict) else str(method_data)
        try:
            method = AttackMethod(method_str)
        except ValueError:
            method = AttackMethod.RUNTIME_INJECTION

        return cls(
            id=str(attack.get("id", "")),
            name=attack.get("name", ""),
            description=attack.get("description", ""),
            method=method,
            surfaces=surfaces_data.get("primary", []) if isinstance(surfaces_data, dict) else [],
            fallback_surfaces=surfaces_data.get("fallback", []) if isinstance(surfaces_data, dict) else [],
            payload_template=payload_data.get("template", "") if isinstance(payload_data, dict) else str(payload_data),
            payload_style=payload_data.get("style", "contextual") if isinstance(payload_data, dict) else "contextual",
            target_patterns=target_data.get("file_patterns", []) if isinstance(target_data, dict) else [],
            inject_position=target_data.get("inject_position", "append") if isinstance(target_data, dict) else "append",
            inject_prefix=target_data.get("inject_prefix", "") if isinstance(target_data, dict) else "",
            success_signals=success_data.get("signals", []) if isinstance(success_data, dict) else [],
            metadata=attack.get("metadata", {}),
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format for serialization."""
        return {
            "attack": {
                "id": self.id,
                "name": self.name,
                "description": self.description,
                "method": {"type": self.method.value},
                "surfaces": {
                    "primary": self.surfaces,
                    "fallback": self.fallback_surfaces,
                },
                "payload": {
                    "template": self.payload_template,
                    "style": self.payload_style,
                },
                "target": {
                    "file_patterns": self.target_patterns,
                    "inject_position": self.inject_position,
                    "inject_prefix": self.inject_prefix,
                },
                "success_criteria": {
                    "signals": self.success_signals,
                },
                "metadata": self.metadata,
            }
        }


@dataclass
class SurfaceDefinition:
    """Definition of a surface type and its associated objects.
    
    Attributes:
        surface_type: Type of surface (FILE_CONTENT, FILE_NAME, etc.)
        files: List of file patterns that map to this surface
        objects: List of object identifiers (for non-file surfaces)
    """
    surface_type: str
    files: List[str] = field(default_factory=list)
    objects: List[str] = field(default_factory=list)


@dataclass
class TaskConfig:
    """Configuration for a task.

    This class represents the new TOML-based task configuration format.
    Each task has its own directory with configuration files, environment setup,
    solutions, and tests.

    Attributes:
        task_id: Unique task identifier
        category: Task category (e.g., "File Organization", "Testing")
        user_goal: Description of what the user wants to accomplish
        prompt_example: The prompt/instruction given to the agent
        expected_surfaces: List of surface types expected to be touched
        script_test: Description of how to test task completion
        groundtruth_goal: Expected final state after task completion
        base_path: Path to the task directory
        surfaces: Dictionary mapping surface types to SurfaceDefinition objects
    """
    task_id: str
    category: str = ""
    user_goal: str = ""
    prompt_example: str = ""
    expected_surfaces: List[str] = field(default_factory=list)
    script_test: str = ""
    groundtruth_goal: str = ""
    base_path: Optional[Path] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    surfaces: Dict[str, SurfaceDefinition] = field(default_factory=dict)

    @classmethod
    def from_toml(cls, path: Path) -> "TaskConfig":
        """Load task configuration from a TOML file.

        Args:
            path: Path to task.toml file

        Returns:
            TaskConfig instance
        """
        if toml is None:
            raise ImportError("toml library required. Install with: pip install toml")

        if hasattr(toml, 'load'):
            with open(path, 'r') as f:
                data = toml.load(f)
        else:
            with open(path, 'rb') as f:
                data = toml.load(f)

        task = data.get("task", {})
        config = cls(
            task_id=str(task.get("id", "")),
            category=task.get("category", ""),
            user_goal=task.get("user_goal", ""),
            prompt_example=task.get("prompt_example", ""),
            expected_surfaces=task.get("expected_surfaces", []),
            script_test=task.get("script_test", ""),
            groundtruth_goal=task.get("groundtruth_goal", ""),
            base_path=path.parent,
            metadata=task.get("metadata", {}),
        )
        
        # Load surface definitions from benign.toml overlay
        config.load_surfaces()
        
        return config
    
    def load_surfaces(self):
        """Load surface definitions from benign.toml overlay.
        
        Reads the surfaces section from environment/overlays/benign.toml
        and populates the surfaces dictionary.
        """
        if not self.base_path:
            return
        
        benign_path = self.base_path / "environment" / "overlays" / "benign.toml"
        if not benign_path.exists():
            return
        
        if toml is None:
            return
        
        try:
            if hasattr(toml, 'load'):
                with open(benign_path, 'r') as f:
                    data = toml.load(f)
            else:
                with open(benign_path, 'rb') as f:
                    data = toml.load(f)
            
            surfaces_data = data.get("surfaces", {})
            for surface_name, surface_info in surfaces_data.items():
                if isinstance(surface_info, dict):
                    surface_type = surface_info.get("type", surface_name.upper())
                    files = surface_info.get("files", [])
                    objects = surface_info.get("objects", [])
                    
                    # Normalize files and objects to lists
                    files_list = files if isinstance(files, list) else [files] if files else []
                    objects_list = objects if isinstance(objects, list) else [objects] if objects else []
                    
                    # Merge with existing surface if it already exists (same type)
                    if surface_type in self.surfaces:
                        existing = self.surfaces[surface_type]
                        # Merge files, avoiding duplicates
                        merged_files = list(set(existing.files + files_list))
                        merged_objects = list(set(existing.objects + objects_list))
                        self.surfaces[surface_type] = SurfaceDefinition(
                            surface_type=surface_type,
                            files=merged_files,
                            objects=merged_objects,
                        )
                    else:
                        self.surfaces[surface_type] = SurfaceDefinition(
                            surface_type=surface_type,
                            files=files_list,
                            objects=objects_list,
                        )
        except Exception as e:
            # Log but don't fail if surfaces can't be loaded
            import logging
            logging.getLogger(__name__).warning(f"Failed to load surfaces from {benign_path}: {e}")

    @classmethod
    def from_dict(cls, data: Dict[str, Any], base_path: Optional[Path] = None) -> "TaskConfig":
        """Create TaskConfig from a dictionary (e.g., from BENIGN_TASKS.json).

        Args:
            data: Dictionary with task configuration
            base_path: Optional base path for the task

        Returns:
            TaskConfig instance
        """
        return cls(
            task_id=str(data.get("task_id", "")),
            category=data.get("task_category", ""),
            user_goal=data.get("user_goal", ""),
            prompt_example=data.get("prompt_example", ""),
            expected_surfaces=data.get("expected_surfaces", []),
            script_test=data.get("script_test", ""),
            groundtruth_goal=data.get("groundtruth_goal", ""),
            base_path=base_path,
            metadata=data.get("metadata", {}),
        )

    def get_instruction(self) -> str:
        """Get the instruction/prompt for the agent.

        First tries to read from instruction.txt, falls back to prompt_example.

        Returns:
            The instruction text for the agent
        """
        if self.base_path:
            instruction_path = self.base_path / "instruction.txt"
            if instruction_path.exists():
                return instruction_path.read_text().strip()
        return self.prompt_example


    def get_attack_config(self, attack_id: str) -> Optional[AttackConfig]:
        """Get a specific attack configuration by ID.

        Args:
            attack_id: The attack ID to retrieve

        Returns:
            AttackConfig if found, None otherwise
        """
        # First try global attacks directory
        tasks_root = self.base_path.parent if self.base_path else Path("tasks")
        attacks_root = tasks_root.parent / "attacks" if tasks_root.parent else Path("attacks")
        attack_path = attacks_root / f"attack_{attack_id}" / "config.toml"
        
        if attack_path.exists():
            return AttackConfig.from_toml(attack_path)

        # Fallback to task-specific overlays (backward compatibility)
        if self.base_path:
            attack_path = self.base_path / "environment" / "overlays" / f"attack_{attack_id}.toml"
            if attack_path.exists():
                return AttackConfig.from_toml(attack_path)

        # Search all attack files
        for attack in self.get_attack_configs():
            if attack.id == attack_id:
                return attack

        return None
    
    def get_attack_configs(self) -> List[AttackConfig]:
        """Get all attack configurations for this task.

        First tries global attacks directory, then falls back to task-specific overlays.

        Returns:
            List of AttackConfig instances
        """
        attacks = []
        
        # Try global attacks directory first
        tasks_root = self.base_path.parent if self.base_path else Path("tasks")
        attacks_root = tasks_root.parent / "attacks" if tasks_root.parent else Path("attacks")
        
        if attacks_root.exists():
            for attack_dir in sorted(attacks_root.glob("attack_*")):
                if attack_dir.is_dir():
                    config_path = attack_dir / "config.toml"
                    if config_path.exists():
                        try:
                            attacks.append(AttackConfig.from_toml(config_path))
                        except Exception as e:
                            import logging
                            logging.getLogger(__name__).warning(f"Failed to load attack config {config_path}: {e}")
        
        # Fallback to task-specific overlays (backward compatibility)
        if not attacks and self.base_path:
            overlays_dir = self.base_path / "environment" / "overlays"
            if overlays_dir.exists():
                for f in overlays_dir.glob("attack_*.toml"):
                    try:
                        attacks.append(AttackConfig.from_toml(f))
                    except Exception as e:
                        import logging
                        logging.getLogger(__name__).warning(f"Failed to load attack config {f}: {e}")

        return attacks

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format for serialization."""
        return {
            "task_id": self.task_id,
            "task_category": self.category,
            "user_goal": self.user_goal,
            "prompt_example": self.prompt_example,
            "expected_surfaces": self.expected_surfaces,
            "script_test": self.script_test,
            "groundtruth_goal": self.groundtruth_goal,
            "metadata": self.metadata,
        }


def load_task_config(task_dir: Path) -> TaskConfig:
    """Load task configuration from a task directory.

    Args:
        task_dir: Path to task directory (e.g., tasks/task_1/)

    Returns:
        TaskConfig instance

    Raises:
        FileNotFoundError: If task.toml doesn't exist
    """
    task_toml = task_dir / "task.toml"
    if not task_toml.exists():
        raise FileNotFoundError(f"task.toml not found in {task_dir}")

    return TaskConfig.from_toml(task_toml)


def load_all_tasks(tasks_root: Path) -> List[TaskConfig]:
    """Load all task configurations from a tasks directory.

    Args:
        tasks_root: Root directory containing task_* subdirectories

    Returns:
        List of TaskConfig instances
    """
    tasks = []
    for task_dir in sorted(tasks_root.glob("task_*")):
        if task_dir.is_dir():
            try:
                tasks.append(load_task_config(task_dir))
            except Exception as e:
                print(f"Warning: Failed to load task from {task_dir}: {e}")

    return tasks
