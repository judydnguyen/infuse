"""Defense registry: ``name -> factory``. The CLI's ``--defense`` choices are this dict's keys."""
from __future__ import annotations

from typing import Callable, Optional

from infuse.defenses import (
    CamelStyleDefense, Defense, DefensePipeline, DelimiterIsolationDefense, InputFilterDefense,
    InputTransformDefense, InstructionalHardeningDefense, LlamaGuardDefense, NoDefense, OutputFilterDefense,
    ProgentDefense, QwenGuardDefense,
)

ModelFn = Optional[Callable[[str], str]]


def _pipeline(model_fn: ModelFn) -> Defense:
    parts: list[Defense] = [DelimiterIsolationDefense(), InstructionalHardeningDefense()]
    if model_fn:
        parts += [InputFilterDefense(model_fn=model_fn), OutputFilterDefense(model_fn=model_fn)]
    return DefensePipeline(parts)


#: name -> (factory(model_fn) -> Defense, needs_model)
DEFENSES: dict[str, tuple[Callable[[ModelFn], Defense], bool]] = {
    "none": (lambda m: NoDefense(), False),
    "delimiter_isolation": (lambda m: DelimiterIsolationDefense(), False),
    "instructional_hardening": (lambda m: InstructionalHardeningDefense(), False),
    "input_filter": (lambda m: InputFilterDefense(model_fn=m), True),
    "input_transform": (lambda m: InputTransformDefense(model_fn=m), True),
    "output_filter": (lambda m: OutputFilterDefense(model_fn=m), True),
    "pipeline": (_pipeline, False),
    "llama_guard": (lambda m: LlamaGuardDefense(), False),
    "qwen_guard": (lambda m: QwenGuardDefense(), False),
    "progent": (lambda m: ProgentDefense(model_fn=m), True),
    "camel": (lambda m: CamelStyleDefense(model_fn=m), True),
}

DEFENSE_NAMES: tuple[str, ...] = tuple(DEFENSES)


def needs_model(name: str) -> bool:
    return DEFENSES[_norm(name)][1]


def build_defense(name: str | None, defense_model: str | None = None) -> Defense:
    """Instantiate a defense by name; LLM-backed ones get a ``model_fn`` from :mod:`infuse.registry.models`."""
    key = _norm(name)
    if key not in DEFENSES:
        raise ValueError(f"Unknown defense {name!r}. Choose from: {', '.join(DEFENSE_NAMES)}")
    factory, requires = DEFENSES[key]
    model_fn: ModelFn = None
    if defense_model:
        from infuse.registry.models import defense_model_fn
        model_fn = defense_model_fn(defense_model)
    elif requires:
        raise ValueError(f"Defense {key!r} needs --defense-model")
    return factory(model_fn)


def _norm(name: str | None) -> str:
    return (name or "none").strip().lower()


__all__ = ["DEFENSES", "DEFENSE_NAMES", "build_defense", "needs_model"]
