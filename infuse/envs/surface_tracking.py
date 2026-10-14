"""
Surface Tracking Utilities
Helper functions for tracking surface events during agent execution.
Attacks are injected at build time, not at runtime.
"""

from typing import Protocol, Dict, Any, Optional, Set
from infuse.tasks.task_suite import SurfaceType, SurfaceEvent, ExecutionTrace
from infuse.attacks.base_attack import Attack
from .surface_detector import detect_surfaces_from_action


class Environment(Protocol):
    """Protocol for environments that can be wrapped."""
    config: Any
    def execute(self, command: str, cwd: str = "") -> Dict[str, Any]: ...
    def get_template_vars(self) -> Dict[str, Any]: ...


class SurfaceTrackingWrapper:
    """
    Wraps an environment to track surface events.

    This wrapper intercepts environment operations and:
    1. Tracks surface events (FILE_READ, TERMINAL_OUTPUT, etc.)
    2. Builds an ExecutionTrace

    Note: Attack injection happens at build time (in Docker image), NOT at runtime.
    """

    def __init__(
        self,
        base_env: Environment,
        attack: Optional[Attack] = None,
        trace: Optional[ExecutionTrace] = None,
    ):
        self.base_env = base_env
        self.config = base_env.config
        self.attack = attack  # Kept for metadata/tracking only, not for injection
        self.trace = trace or ExecutionTrace(task_id="unknown")
        self.step_count = 0

    def execute(self, command: str, cwd: str = "") -> Dict[str, Any]:
        """
        Execute command and track surface events.

        Attack injection is NOT done here - it happens at build time.
        """
        self.step_count += 1

        # Execute command to get raw output
        result = self.base_env.execute(command, cwd)

        # Get output content
        output_content = result.get("output", "") or result.get("stdout", "")

        # Track surface events for object tracking
        detected_surfaces = detect_surfaces_from_action(command, output_content)

        # Track ALL detected surfaces (READ and WRITE) for object tracking
        from infuse.envs.surface_detector import get_object_id
        for surface in detected_surfaces:
            obj_id = get_object_id(command, surface, cwd if cwd else None)
            path = None
            if obj_id and ":" in obj_id:
                path = obj_id.split(":", 1)[1]
            elif obj_id:
                path = obj_id

            surface_event = SurfaceEvent(
                surface=surface,
                content=command,
                path=path,
                step=self.step_count
            )
            self.trace.add_event(surface_event)

        return result

    def get_current_surfaces(self) -> Set[SurfaceType]:
        """Get all surfaces detected in the current execution."""
        if not self.trace.events:
            return set()
        return {e.surface for e in self.trace.events}

    def get_template_vars(self) -> Dict[str, Any]:
        """Get template variables from base environment."""
        return self.base_env.get_template_vars()

    def track_file_read(self, path: str, content: str):
        """Manually track a file read event."""
        self.step_count += 1
        event = SurfaceEvent(
            surface=SurfaceType.FILE_READ,
            content=content,
            path=path,
            step=self.step_count
        )
        self.trace.add_event(event)
        return content

    def track_file_write(self, path: str, content: str):
        """Manually track a file write event."""
        self.step_count += 1
        event = SurfaceEvent(
            surface=SurfaceType.FILE_WRITE,
            content=content,
            path=path,
            step=self.step_count
        )
        self.trace.add_event(event)
        return content


def wrap_environment_with_surface_tracking(
    base_env: Environment,
    attack: Optional[Attack] = None,
    trace: Optional[ExecutionTrace] = None,
) -> SurfaceTrackingWrapper:
    """
    Convenience function to wrap an environment with surface tracking.

    Args:
        base_env: The base environment to wrap
        attack: Optional Attack instance (for metadata only, not injection)
        trace: Optional ExecutionTrace to use (creates new one if not provided)

    Returns:
        SurfaceTrackingWrapper instance
    """
    return SurfaceTrackingWrapper(base_env, attack, trace)
