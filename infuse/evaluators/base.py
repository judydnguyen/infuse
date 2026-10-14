"""
Base evaluator classes for task evaluation.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, Any, Optional


@dataclass
class EvaluationResult:
    """Result of an evaluation."""
    success: bool
    score: float
    stdout: Optional[str] = None
    stderr: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class TaskEvaluator(ABC):
    """Base class for task evaluators."""
    
    @abstractmethod
    def evaluate(
        self,
        trace: Any,  # ExecutionTrace from tasks.task_suite
        workdir: str,
    ) -> EvaluationResult:
        """
        Evaluate a task execution trace.
        
        Args:
            trace: ExecutionTrace object containing task execution information
            workdir: Working directory where task was executed
            
        Returns:
            EvaluationResult with success status and score
        """
        pass
