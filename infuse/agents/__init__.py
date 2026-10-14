"""Agent implementations.

``infuse.agents.minisweagent`` is a vendored copy of mini-swe-agent whose internal
modules import each other as ``minisweagent.*``. We expose that name by putting
this directory on ``sys.path`` once, here, so every import path
(``infuse.agents.minisweagent...`` or ``minisweagent...``) resolves to the same files.
"""
import sys
from pathlib import Path

_HERE = str(Path(__file__).resolve().parent)
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)
