from dataclasses import dataclass
from typing import List, Optional
from infuse.tasks.task_suite import SurfaceType

@dataclass
class OutputSegment:
    text: str
    tainted: bool
    surface: Optional[SurfaceType] = None
    object_id: Optional[str] = None

@dataclass
class ToolObservation:
    tool: str
    returncode: int
    segments: List[OutputSegment]
