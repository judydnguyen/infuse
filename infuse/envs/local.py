"""
Local Environment
Executes bash commands directly on the local machine.
"""

import os
import platform
import subprocess
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class LocalEnvironmentConfig:
    """Configuration for local environment execution."""
    cwd: str = ""
    """Working directory for command execution."""
    env: dict[str, str] = field(default_factory=dict)
    """Environment variables to set."""
    timeout: int = 30
    """Timeout for command execution in seconds."""


class LocalEnvironment:
    """Executes bash commands directly on the local machine."""
    
    def __init__(self, *, config_class: type = LocalEnvironmentConfig, **kwargs):
        """
        Initialize local environment.
        
        Args:
            config_class: Configuration class to use
            **kwargs: Configuration parameters (cwd, env, timeout, etc.)
        """
        self.config = config_class(**kwargs)

    def execute(self, command: str, cwd: str = "", *, timeout: int | None = None) -> dict[str, Any]:
        """
        Execute a command in the local environment and return the result as a dict.
        
        Args:
            command: Bash command to execute
            cwd: Working directory (overrides config.cwd if provided)
            timeout: Command timeout in seconds (overrides config.timeout if provided)
            
        Returns:
            Dictionary with 'output' (stdout) and 'returncode' keys
        """
        cwd = cwd or self.config.cwd or os.getcwd()
        # Ensure the working directory exists and is accessible
        if cwd:
            cwd_path = Path(cwd)
            if not cwd_path.exists():
                try:
                    cwd_path.mkdir(parents=True, exist_ok=True)
                except (PermissionError, OSError):
                    # If we can't create it, try to use parent or fallback to current dir
                    pass
        
        # Merge environment variables, ensuring PWD is set correctly
        env = os.environ.copy()
        env.update(self.config.env)
        if cwd:
            env["PWD"] = str(Path(cwd).resolve())
        
        result = subprocess.run(
            command,
            shell=True,
            text=True,
            cwd=cwd,
            env=env,
            timeout=timeout or self.config.timeout,
            encoding="utf-8",
            errors="replace",
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        return {"output": result.stdout, "returncode": result.returncode}

    def get_template_vars(self) -> dict[str, Any]:
        """
        Get template variables for rendering templates.
        
        Returns:
            Dictionary of template variables (config, system info, environment)
        """
        return asdict(self.config) | platform.uname()._asdict() | os.environ
