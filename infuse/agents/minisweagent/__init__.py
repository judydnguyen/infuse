"""
This file provides:

- Path settings for global config file & relative directories
- Version numbering
- Protocols for the core components of mini-swe-agent.
  By the magic of protocols & duck typing, you can pretty much ignore them,
  unless you want the static type checking.
"""

__version__ = "1.14.4"

import os
import sys
from pathlib import Path
from typing import Any, Protocol

import dotenv
from rich.console import Console

# Add agents/ directory to sys.path so absolute imports work
# This allows using "from minisweagent.xxx import yyy" instead of relative imports
_package_dir = Path(__file__).resolve().parent
_agents_dir = _package_dir.parent
if str(_agents_dir) not in sys.path:
    sys.path.insert(0, str(_agents_dir))

from .utils.log import logger

package_dir = _package_dir

# Load config directly from a local .env file (typically in the current working directory).
# You can override the path with MSWEA_DOTENV_FILE.
global_config_file = Path(os.getenv("MSWEA_DOTENV_FILE") or ".env").expanduser().resolve()
global_config_dir = global_config_file.parent

if not os.getenv("MSWEA_SILENT_STARTUP"):
    Console().print(
        f"👋 This is [bold green]mini-swe-agent[/bold green] version [bold green]{__version__}[/bold green].\n"
        f"Loading config from [bold green]'{global_config_file}'[/bold green]"
    )
dotenv.load_dotenv(dotenv_path=global_config_file)


# === Protocols ===
# You can ignore them unless you want static type checking.


class Model(Protocol):
    """Protocol for language models."""

    config: Any
    cost: float
    n_calls: int

    def query(self, messages: list[dict[str, str]], **kwargs) -> dict: ...

    def get_template_vars(self) -> dict[str, Any]: ...


class Environment(Protocol):
    """Protocol for execution environments."""

    config: Any

    def execute(self, command: str, cwd: str = "") -> dict[str, str]: ...

    def get_template_vars(self) -> dict[str, Any]: ...


class Agent(Protocol):
    """Protocol for agents."""

    model: Model
    env: Environment
    messages: list[dict[str, str]]
    config: Any

    def run(self, task: str, **kwargs) -> tuple[str, str]: ...


__all__ = [
    "Agent",
    "Model",
    "Environment",
    "package_dir",
    "__version__",
    "global_config_file",
    "global_config_dir",
    "logger",
]
