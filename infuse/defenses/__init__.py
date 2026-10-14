"""Defense mechanisms for INFUSE.

Public API
----------
Base classes::

    Defense          — base class; override any of three hook methods
    NoDefense        — explicit no-op
    DefensePipeline  — compose defenses in sequence

Observation-level defenses (apply_to_observation / apply_to_instruction /
check_output hooks)::

    InputFilterDefense          — LLM judge blocks malicious observations
    InputTransformDefense       — LLM rewriter neutralizes instruction language
    DelimiterIsolationDefense   — wraps each obs in trust-boundary delimiters
    InstructionalHardeningDefense — hardens task prompt + per-step reminder
    OutputFilterDefense         — LLM judge gates actions before execution

Runtime, system-level privilege control (check_output gate over bash)::

    ProgentDefense       — least-privilege command allowlist from trusted task
    CamelStyleDefense    — capability/data-flow gate frozen from trusted task

Constants::

    BLOCKED_INPUT   — placeholder returned when an observation is blocked
    BLOCKED_ACTION  — shell command substituted when an action is blocked
"""

from infuse.defenses.base import (
    Defense,
    NoDefense,
    DefensePipeline,
    BLOCKED_INPUT,
    BLOCKED_ACTION,
)
from infuse.defenses.observation import (
    InputFilterDefense,
    InputTransformDefense,
    DelimiterIsolationDefense,
    InstructionalHardeningDefense,
    OutputFilterDefense,
)
from infuse.defenses.runtime.content_safety import LlamaGuardDefense, QwenGuardDefense
from infuse.defenses.runtime.privilege_control import ProgentDefense, CamelStyleDefense

__all__ = [
    # Base
    "Defense",
    "NoDefense",
    "DefensePipeline",
    "BLOCKED_INPUT",
    "BLOCKED_ACTION",
    # Observation-level
    "InputFilterDefense",
    "InputTransformDefense",
    "DelimiterIsolationDefense",
    "InstructionalHardeningDefense",
    "OutputFilterDefense",
    # Runtime — content safety classifiers
    "LlamaGuardDefense",
    "QwenGuardDefense",
    # Runtime — system-level privilege control
    "ProgentDefense",
    "CamelStyleDefense",
]
