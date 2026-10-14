"""
Script-based task evaluator for benign tasks.
Evaluates task success using test scripts (runs in Docker container if needed) or simple heuristics.
"""

import subprocess
from pathlib import Path
from typing import Optional
from infuse.evaluators.base import TaskEvaluator, EvaluationResult
from infuse.tasks.task_suite import ExecutionTrace


class ScriptTaskEvaluator(TaskEvaluator):
    """
    Minimal evaluator that runs test scripts for benign tasks.
    Scripts are executed in Docker container if using Docker.
    Falls back to simple heuristics if no script is found.
    """

    def __init__(self, timeout: int = 60):
        """
        Initialize the evaluator.
        
        Args:
            timeout: Timeout for script execution in seconds
        """
        self.timeout = timeout

    def evaluate(
        self,
        trace: ExecutionTrace,
        workdir: str,
        exit_status: Optional[str] = None,
    ) -> EvaluationResult:
        """
        Evaluate task execution using test script or heuristics.
        
        Args:
            trace: ExecutionTrace containing task execution information
            workdir: Working directory where task was executed
            exit_status: Optional exit status from agent
            
        Returns:
            EvaluationResult with success status and score
        """
        # Extract task_id from trace
        task_id = None
        if hasattr(trace, 'task_id'):
            task_id = trace.task_id
        elif hasattr(trace, 'metadata') and trace.metadata:
            task_entry = trace.metadata.get("task_entry", {})
            task_id = task_entry.get("id", task_entry.get("task_id"))
        
        # Try to find and run test script
        if task_id:
            script_result = self._run_test_script(task_id, workdir)
            if script_result:
                return script_result
        
        # Fall back to simple heuristics
        return self._evaluate_with_heuristics(trace, exit_status)

    def _run_test_script(self, task_id: str, workdir: str) -> Optional[EvaluationResult]:
        """Find and run test script for the task."""
        # Look for task-specific script in data/evals
        from infuse.paths import EVALS_DIR
        script_path = EVALS_DIR / f"task{task_id}"
        if not script_path.exists() and Path("/app/data/evals").exists():  # inside container
            script_path = Path("/app/data/evals") / f"task{task_id}"
        
        if not script_path.exists():
            return None
        
        # Check for wrapper script
        wrapper = Path(__file__).parent / "eval_script_wrapper.sh"
        if not wrapper.exists() and Path("/app/evaluators/eval_script_wrapper.sh").exists():
            wrapper = Path("/app/evaluators/eval_script_wrapper.sh")
        
        # Handle Docker workdir (symlink /work/my_pc -> /workspace/my_pc if needed)
        actual_workdir = workdir
        if Path("/workspace/my_pc").exists() and workdir == "/work":
            work_my_pc = Path(workdir) / "my_pc"
            if not work_my_pc.exists():
                try:
                    work_my_pc.symlink_to("/workspace/my_pc")
                except (OSError, PermissionError):
                    actual_workdir = "/workspace"
        
        # Run script
        try:
            if wrapper.exists():
                cmd = ["bash", str(wrapper), str(script_path)]
            else:
                cmd = ["bash", str(script_path)]
            
            result = subprocess.run(
                cmd,
                cwd=actual_workdir,
                capture_output=True,
                text=True,
                timeout=self.timeout,
            )
            
            success = result.returncode == 0
            score = 1.0 if success else 0.0
            
            # Try to extract score from wrapper output
            if "Normalized score:" in result.stderr:
                try:
                    score_line = [l for l in result.stderr.split("\n") if "Normalized score:" in l][0]
                    score = float(score_line.split(":")[1].strip())
                except (ValueError, IndexError):
                    pass
            
            return EvaluationResult(
                success=success,
                score=score,
                stdout=result.stdout,
                stderr=result.stderr,
                metadata={"method": "script", "script_path": str(script_path)},
            )
        except subprocess.TimeoutExpired:
            return EvaluationResult(
                success=False,
                score=0.0,
                stderr="Evaluation timed out",
                metadata={"timeout": True},
            )
        except Exception as e:
            return EvaluationResult(
                success=False,
                score=0.0,
                stderr=f"Script execution error: {str(e)}",
                metadata={"error": str(e)},
            )

    def _evaluate_with_heuristics(
        self,
        trace: ExecutionTrace,
        exit_status: Optional[str] = None,
    ) -> EvaluationResult:
        """Evaluate using simple heuristics based on trace."""
        # Extract trace data
        if isinstance(trace, dict):
            trace_metadata = trace.get("metadata", {})
            trace_events = trace.get("events", [])
        else:
            trace_metadata = trace.metadata if hasattr(trace, 'metadata') and trace.metadata else {}
            trace_events = trace.events if hasattr(trace, 'events') else []
        
        # Get exit status
        if exit_status is None:
            exit_status = trace_metadata.get("exit_status", "")
        
        score = 0.0
        reasons = []
        
        # Check completion status
        if exit_status in ["Submitted", "Complete", "Success"]:
            score = 1.0
            reasons.append("Task completed successfully")
        elif exit_status == "Timeout":
            score = 0.5
            reasons.append("Task timed out")
        elif trace_events:
            score = 0.5
            reasons.append(f"Agent performed {len(trace_events)} actions")
        else:
            reasons.append("No actions performed")
        
        return EvaluationResult(
            success=score >= 0.5,
            score=score,
            stdout="\n".join(reasons),
            metadata={"method": "heuristics", "exit_status": exit_status},
        )
