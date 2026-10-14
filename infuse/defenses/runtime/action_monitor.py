"""
Action Monitor
Monitors agent actions at runtime and blocks dangerous operations.
"""

from typing import Dict, List, Any, Optional, Tuple
from enum import Enum


class ActionSeverity(Enum):
    SAFE = "safe"
    WARNING = "warning"
    DANGEROUS = "dangerous"
    BLOCKED = "blocked"


class ActionMonitor:
    """Monitors and controls agent actions at runtime."""
    
    def __init__(self, config: Optional[Dict] = None):
        """
        Initialize action monitor.
        
        Args:
            config: Configuration dictionary
        """
        self.config = config or {}
        self.blocked_actions = self.config.get("blocked_actions", [])
        self.allowed_paths = self.config.get("allowed_paths", ["./", "/tmp/"])
        self.action_history = []
        
    def check_action(self, action: Dict[str, Any]) -> Tuple[ActionSeverity, str]:
        """
        Check if an action should be allowed.
        
        Args:
            action: Action to check
            
        Returns:
            Tuple of (severity, reason)
        """
        action_type = action.get("type", "")
        
        # Check blocked actions
        if action_type in self.blocked_actions:
            return ActionSeverity.BLOCKED, f"Action type '{action_type}' is blocked"
        
        # Check file operations
        if "file" in action_type:
            file_path = action.get("file_path", "")
            if not self._is_path_allowed(file_path):
                return ActionSeverity.BLOCKED, f"File path '{file_path}' is not allowed"
        
        # Check code execution
        if "execution" in action_type or "code" in action_type:
            code = action.get("code", "")
            if self._is_code_dangerous(code):
                return ActionSeverity.DANGEROUS, "Code contains dangerous patterns"
        
        # Record action
        self.action_history.append(action)
        
        return ActionSeverity.SAFE, "Action allowed"
    
    def _is_path_allowed(self, file_path: str) -> bool:
        """Check if a file path is allowed."""
        for allowed_path in self.allowed_paths:
            if file_path.startswith(allowed_path):
                return True
        return False
    
    def _is_code_dangerous(self, code: str) -> bool:
        """Check if code contains dangerous patterns."""
        dangerous_patterns = [
            "eval", "exec", "__import__", "subprocess",
            "os.system", "rm -rf", "format"
        ]
        code_lower = code.lower()
        return any(pattern in code_lower for pattern in dangerous_patterns)
    
    def get_history(self) -> List[Dict[str, Any]]:
        """Get action history."""
        return self.action_history.copy()
