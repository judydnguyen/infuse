"""
Base Attack classes for injecting malicious content into agent interactions.
"""

from abc import ABC, abstractmethod
from typing import Optional, TYPE_CHECKING
from infuse.tasks.task_suite import SurfaceType, SurfaceEvent, ExecutionTrace

if TYPE_CHECKING:
    from infuse.envs.observation_model import OutputSegment

# Re-export surface-aware attacks for convenience
try:
    __all__ = [
        "Attack",
        "SingleSurfaceInjection",
        "MultiSurfacePersistentInjection",
        "SurfaceAwareAttack",
        "AdaptiveSurfaceAttack",
    ]
except ImportError:
    __all__ = [
        "Attack",
        "SingleSurfaceInjection",
        "MultiSurfacePersistentInjection",
    ]


class Attack(ABC):
    """Base class for attack implementations."""
    
    def __init__(self, attack_id: str, target_surfaces: set[SurfaceType]):
        self.attack_id = attack_id
        self.target_surfaces = target_surfaces
        self.attacked_objects: set[str] = set()  # Track which objects have been attacked
        self.attacked_surfaces_without_objects: set[SurfaceType] = set()  # Track surfaces attacked without specific object IDs (for lock-in)

    def reset(self):
        """Clear internal state per run."""
        self.attacked_objects.clear()
        self.attacked_surfaces_without_objects.clear()
    
    def _get_object_id(self, event: SurfaceEvent, action: str = "") -> Optional[str]:
        """
        Get unique identifier for the object touched by this surface event.
        
        Args:
            event: Surface event
            action: Optional action string for extracting object ID
            
        Returns:
            Object identifier string, or None if object cannot be identified
        """
        from infuse.envs.surface_detector import get_object_id
        return get_object_id(action or event.content, event.surface, event.path)
    
    def _should_attack_object(self, event: SurfaceEvent, action: str = "") -> bool:
        """
        Check if this object should be attacked (hasn't been attacked yet).
        
        Args:
            event: Surface event
            action: Optional action string
            
        Returns:
            True if object should be attacked, False if already attacked
        """
        object_id = self._get_object_id(event, action)
        if object_id is None:
            # No specific object (e.g., TERMINAL_OUTPUT) - allow attack once per step
            # Use step number as identifier
            step_id = f"step_{event.step}"
            if step_id in self.attacked_objects:
                return False
            self.attacked_objects.add(step_id)
            return True
        
        # Check if this specific object has been attacked
        if object_id in self.attacked_objects:
            return False
        
        # Mark this object as attacked
        self.attacked_objects.add(object_id)
        return True

    @abstractmethod
    def on_surface_event(
        self,
        event: SurfaceEvent,
        trace: ExecutionTrace,
        action: str = "",
        skip_object_check: bool = False,
    ) -> str | None:
        """
        Return injected content if attack triggers, otherwise None.
        
        NOTE: This method is primarily for legacy code paths. The new injection pipeline
        uses on_segment() instead. If you override this method, make sure to call
        trace.record_attacked_object() when an attack is injected.
        
        Args:
            event: The surface event that triggered this check
            trace: The current execution trace
            action: Optional action string for object ID extraction
            skip_object_check: If True, skip the object attack check (assumes it was already done)
            
        Returns:
            Injected content string if attack should trigger, None otherwise
        """
        return None
    
    def on_segment(
        self,
        segment,
        trace: ExecutionTrace,
    ) -> str | None:
        """
        Return injected payload if attack should apply to this segment, otherwise None.
        
        Attacks operate on what the agent sees (segments), not what it executes.
        This enables partial injection - only certain segments may be injected.
        
        Args:
            segment: The output segment (with taint, surface, object_id)
            trace: The current execution trace
            
        Returns:
            Payload string to inject into this segment, or None
        """
        # Default implementation: check if segment is tainted and object hasn't been attacked
        if not segment.tainted:
            return None
        
        # Check if this surface is a target
        if segment.surface and segment.surface not in self.target_surfaces:
            return None
        
        # Object tracking at segment level
        # For persistent attacks (SingleSurfaceInjection), allow re-injection
        # For one-time attacks, check if already attacked
        from infuse.attacks.base_attack import SingleSurfaceInjection
        is_persistent = isinstance(self, SingleSurfaceInjection)
        
        if segment.object_id and segment.object_id in self.attacked_objects:
            # Check if this is a persistent attack that should re-inject
            if is_persistent:
                # SingleSurfaceInjection: allow re-injection (persistent adversary control)
                # Still record the attack for tracking, but don't skip injection
                pass
            else:
                # Other attacks: skip if already attacked
                return None
        
        # Mark object as attacked (for tracking purposes)
        if segment.object_id:
            self.attacked_objects.add(segment.object_id)
        elif is_persistent and segment.surface:
            # For SingleSurfaceInjection with objects without specific IDs, track by surface type
            # Use consistent ID for lock-in logic
            generic_id = f"{segment.surface.value.lower()}_generic"
            self.attacked_objects.add(generic_id)
            self.attacked_surfaces_without_objects.add(segment.surface)
        
        # Return payload (subclasses can override for custom logic)
        return self._get_payload_for_segment(segment, trace)
    
    def _get_payload_for_segment(
        self,
        segment,
        trace: ExecutionTrace,
    ) -> str | None:
        """
        Get the payload to inject for this segment.
        
        Subclasses should override this method to provide their payload logic.
        
        Args:
            segment: The output segment
            trace: The current execution trace
            
        Returns:
            Payload string or None
        """
        # Default: no payload (subclasses must override)
        return None


class SingleSurfaceInjection(Attack):
    """
    Attack that injects a payload into one or more surface types, persistently attacking
    every matching object multiple times (simulating persistent adversary control).

    When multiple surfaces are provided, ALL of them are attacked independently — every
    file read on any surface in the list triggers injection every time it is accessed.
    """
    
    def __init__(
        self,
        attack_id: str,
        surface: SurfaceType | list[SurfaceType],
        payload: str,
        use_surface_formatting: bool = True,
        formatting_style: str = "contextual",
    ):
        """
        Initialize a single-surface injection attack.
        
        Args:
            attack_id: Unique identifier for this attack
            surface: The surface type(s) to target. Can be a single SurfaceType or a list.
                    All provided surfaces are attacked independently — every matching
                    surface (and every file within that surface) triggers injection.
            payload: The attack payload to inject
            use_surface_formatting: If True, format payload based on surface type
            formatting_style: Style of formatting ("stealthy", "direct", "contextual")
        """
        # Handle both single surface and list of surfaces
        if isinstance(surface, list):
            surfaces_set = set(surface)
            self.surfaces_list = surface  # Keep ordered list for reference
        else:
            surfaces_set = {surface}
            self.surfaces_list = [surface]
        
        super().__init__(attack_id, surfaces_set)
        self.payload = payload
        self.use_surface_formatting = use_surface_formatting
        self.formatting_style = formatting_style

    def on_surface_event(self, event: SurfaceEvent, trace: ExecutionTrace, action: str = "", skip_object_check: bool = False) -> str | None:
        """
        Inject payload when a target surface is accessed, persistently attacking the same object.

        When multiple surfaces are configured, ALL of them are attacked independently —
        the attack fires on every surface in target_surfaces, not just the first one touched.

        Note: SingleSurfaceInjection persistently attacks the same object multiple times,
        unlike MultiSurfacePersistentInjection which attacks each object only once.

        Args:
            event: Surface event
            trace: Execution trace
            action: Optional action string for object ID extraction
            skip_object_check: If True, skip the object attack check (assumes it was already done)
        """
        if event.surface not in self.target_surfaces:
            return None

        # Format payload based on surface if enabled
        if self.use_surface_formatting:
            try:
                from infuse.envs.surface_attack_prompts import format_payload_for_surface
                from infuse.envs.surface_detector import get_surface_context
                
                context = get_surface_context(event.content, event.surface)
                context["path"] = event.path
                
                formatted_payload = format_payload_for_surface(
                    payload=self.payload,
                    surface=event.surface,
                    style=self.formatting_style,
                    context=context
                )
                return event.content + "\n\n" + formatted_payload
            except ImportError:
                # Fallback if formatting not available
                pass
        
        # Default: inject payload as-is
        return event.content + "\n\n" + self.payload
    
    def _get_payload_for_segment(self, segment, trace: ExecutionTrace) -> str | None:
        """
        Return payload for this segment (persistently attacks same object).

        All surfaces in target_surfaces are attacked independently — each matching
        surface/file triggers injection every time it is accessed.
        """
        if not (segment.surface and segment.surface in self.target_surfaces):
            return None

        # SingleSurfaceInjection: Attack persistently (every time, same object)
        # Don't check attacked_objects - allow repeated attacks on same object
        # This simulates persistent adversary control
        
        # Format payload based on surface if enabled
        if self.use_surface_formatting and segment.surface:
            try:
                from infuse.envs.surface_attack_prompts import format_payload_for_surface
                
                context = {
                    "path": segment.object_id,
                    "surface": segment.surface.value,
                }
                
                formatted_payload = format_payload_for_surface(
                    payload=self.payload,
                    surface=segment.surface,
                    style=self.formatting_style,
                    context=context
                )
                return formatted_payload
            except ImportError:
                pass
        
        return self.payload
    
    def reset(self):
        """Reset attack state."""
        super().reset()  # Clear attacked_objects


class MultiSurfacePersistentInjection(Attack):
    """
    Attack that injects different payloads across multiple surfaces.
    
    This attack targets multiple surfaces and ensures each object is only attacked once.
    Once an object is attacked, it remains attacked (persistent across multiple interactions).
    
    The agent can use ANY of the provided surfaces - when a surface is touched, the corresponding
    payload (by surface index) is used. Each surface can be attacked independently.
    """
    
    def __init__(
        self,
        attack_id: str,
        surfaces: list[SurfaceType],
        payloads: list[str],
        use_surface_formatting: bool = True,
        formatting_style: str = "contextual",
    ):
        """
        Initialize a multi-surface persistent injection attack.
        
        Args:
            attack_id: Unique identifier for this attack
            surfaces: List of surface types to target (order matters - determines payload index)
            payloads: List of payloads (one per surface, in order)
            use_surface_formatting: If True, format payloads based on surface type
            formatting_style: Style of formatting ("stealthy", "direct", "contextual")
        """
        super().__init__(attack_id, set(surfaces))
        self.surfaces = surfaces  # Keep ordered list for payload mapping
        self.payloads = payloads
        self.triggered = set()  # Track which surface types have been triggered
        self.use_surface_formatting = use_surface_formatting
        self.formatting_style = formatting_style

    def reset(self):
        """Reset triggered surfaces and attacked objects for a new run."""
        self.triggered.clear()
        # Also reset attacked objects from parent class
        super().reset()

    def on_surface_event(self, event: SurfaceEvent, trace: ExecutionTrace, action: str = "", skip_object_check: bool = False) -> str | None:
        """
        Inject payloads for the specific surface touched (once per object).
        
        The agent can use ANY of the provided surfaces. Each surface maps to its
        corresponding payload based on the order in the surfaces list.
        
        Once an object is attacked, it remains attacked and won't be attacked again.
        This ensures persistence: an object that has been attacked stays attacked.
        
        Args:
            event: Surface event
            trace: Execution trace
            action: Optional action string for object ID extraction
            skip_object_check: If True, skip the object attack check (assumes it was already done)
        """
        if event.surface not in self.target_surfaces:
            return None
        
        # Check if this object has already been attacked (unless skip_object_check is True)
        # This ensures objects stay attacked (persistent)
        if not skip_object_check:
            if not self._should_attack_object(event, action):
                return None  # Object already attacked, don't attack again
        
        # Map surface to its payload index based on position in original surfaces list
        # This allows agent to use ANY of the provided surfaces, each with its own payload
        try:
            idx = self.surfaces.index(event.surface)
        except ValueError:
            # Surface not in list (shouldn't happen, but handle gracefully)
            return None
        
        if idx >= len(self.payloads):
            # Not enough payloads - use last payload as fallback
            idx = len(self.payloads) - 1
        
        payload = self.payloads[idx]
        self.triggered.add(event.surface)  # Track that this surface type was used
        
        # Format payload based on surface if enabled
        if self.use_surface_formatting:
            try:
                from infuse.envs.surface_attack_prompts import format_payload_for_surface
                from infuse.envs.surface_detector import get_surface_context
                
                context = get_surface_context(event.content, event.surface)
                context["path"] = event.path
                
                formatted_payload = format_payload_for_surface(
                    payload=payload,
                    surface=event.surface,
                    style=self.formatting_style,
                    context=context
                )
                return event.content + "\n\n" + formatted_payload
            except ImportError:
                # Fallback if formatting not available
                pass
        
        # Default: inject payload as-is
        return event.content + "\n\n" + payload
    
    def _get_payload_for_segment(self, segment, trace: ExecutionTrace) -> str | None:
        """
        Return payload for this segment (once per object).
        
        Uses the surface's index in the original surfaces list to select the payload.
        This allows the agent to use ANY of the provided surfaces, and each surface
        gets its corresponding payload based on the order in which surfaces were configured.
        """
        # Check if this surface matches any target
        if segment.surface not in self.target_surfaces:
            return None
        
        # Find payload index based on surface's position in the original surfaces list
        # This allows agent to use ANY of the provided surfaces, each with its own payload
        try:
            idx = self.surfaces.index(segment.surface)
        except ValueError:
            # Surface not in list (shouldn't happen, but handle gracefully)
            return None
        
        if idx >= len(self.payloads):
            # Not enough payloads - use last payload as fallback
            idx = len(self.payloads) - 1
        
        payload = self.payloads[idx]
        self.triggered.add(segment.surface)  # Track that this surface type was used
        
        # Format payload based on surface if enabled
        if self.use_surface_formatting and segment.surface:
            try:
                from infuse.envs.surface_attack_prompts import format_payload_for_surface
                
                context = {
                    "path": segment.object_id,
                    "surface": segment.surface.value,
                }
                
                formatted_payload = format_payload_for_surface(
                    payload=payload,
                    surface=segment.surface,
                    style=self.formatting_style,
                    context=context
                )
                return formatted_payload
            except ImportError:
                pass
        
        return payload
