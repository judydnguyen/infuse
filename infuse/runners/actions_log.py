"""Extract the agent's executed shell commands from a trajectory.

Verifiers must judge what the agent *did*, not what the environment showed it
(observations contain the injected payload). The executed action at each step is
the fenced code block in the assistant message, so we collect those and nothing
else — no THOUGHT prose, no observations.
"""
from __future__ import annotations

import re
from typing import Any, Iterable

_FENCE = re.compile(r"```(?:bash|sh|shell|console)?[ \t]*\n(.*?)```", re.DOTALL)


def extract_actions(messages: Iterable[dict[str, Any]] | None) -> str:
    """Return the agent's executed commands, one fenced block per entry."""
    blocks: list[str] = []
    for m in messages or []:
        if not isinstance(m, dict) or m.get("role") != "assistant":
            continue
        content = m.get("content")
        if not isinstance(content, str):
            continue
        for b in _FENCE.findall(content):
            b = b.strip()
            if b:
                blocks.append(b)
    return "\n\n".join(blocks)


__all__ = ["extract_actions"]
