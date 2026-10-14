"""Base defense class and pipeline composer."""

from __future__ import annotations


BLOCKED_INPUT = "[OBSERVATION BLOCKED: potentially malicious content detected]"
BLOCKED_ACTION = "echo '[ACTION BLOCKED: output validation failed]'"


class Defense:
    """Base class for all observation-level defenses.

    Defenses intercept at the agent↔env boundary. Subclasses override one or
    more of the three hook methods:

    - apply_to_observation(obs)  — called every env step, on the raw
      observation string before it is added to the agent's message history.
    - apply_to_instruction(instruction) — called once at session start to
      harden the task prompt.
    - check_output(output) — called on the agent's proposed action before
      env.execute(); return False to block the action.
    """

    name: str = "base"

    def __init__(self) -> None:
        self.events: list = []

    def apply_to_observation(self, obs: str) -> str:
        """Return the (possibly modified) observation.

        Override in subclasses. Default: pass-through.
        """
        return obs

    def apply_to_instruction(self, instruction: str) -> str:
        """Return the (possibly modified) task instruction.

        Called once at session start. Override in subclasses that harden the
        task prompt. Default: pass-through.
        """
        return instruction

    def check_output(self, output: str) -> bool:
        """Return True if the agent action is safe to execute, False to block.

        Override in subclasses that gate actions before execution.
        Default: always safe.
        """
        return True

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self.name!r})"


class NoDefense(Defense):
    """Explicit no-op — use when you want to name the absence of a defense."""

    name = "none"


class DefensePipeline(Defense):
    """Compose multiple defenses in sequence.

    All three hooks are applied in the order the defenses are listed.
    check_output short-circuits on the first False.

    Usage::

        pipeline = DefensePipeline([
            InputFilterDefense(llm_judge),
            DelimiterIsolationDefense(),
            InstructionalHardeningDefense(),
            OutputFilterDefense(model_fn),
        ])
    """

    name = "pipeline"

    def __init__(self, defenses: list[Defense]) -> None:
        self.defenses = defenses

    @property
    def events(self) -> list:
        result = []
        for d in self.defenses:
            result.extend(getattr(d, "events", []))
        return result

    def apply_to_observation(self, obs: str) -> str:
        for d in self.defenses:
            obs = d.apply_to_observation(obs)
        return obs

    def apply_to_instruction(self, instruction: str) -> str:
        for d in self.defenses:
            instruction = d.apply_to_instruction(instruction)
        return instruction

    def check_output(self, output: str) -> bool:
        return all(d.check_output(output) for d in self.defenses)

    def __repr__(self) -> str:
        names = ", ".join(d.name for d in self.defenses)
        return f"DefensePipeline([{names}])"
