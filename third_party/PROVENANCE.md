# Vendored reference implementations

The two system-level privilege-control defenses added for the rebuttal
(`defenses/runtime/privilege_control.py`) are **ports** of the enforcement logic
in these two research artifacts. We vendor the enforcement cores here for
provenance, citation, and to support an optional faithfulness cross-check
against the original harnesses.

Our `Defense` classes are *not* drop-in uses of this code — the originals gate
structured tool calls, whereas mini-swe-agent emits free-form bash. We port the
policy model and evaluation semantics to `Defense.check_output`; see the module
docstring in `defenses/runtime/privilege_control.py` for the exact mapping and
the caveats on faithfulness (esp. the CaMeL *principle* vs. full system).

## Progent

- Paper: Shi et al., "Progent: Programmable Privilege Control for LLM Agents",
  arXiv:2504.11703.
- Source: https://github.com/sunblaze-ucb/progent
- Commit: `8a8eb894b9d568a32b4e58252fea85b47f789c77`
- Vendored: `third_party/progent/secagent/` (policy representation +
  `check_tool_call` / `_check_tool_call` evaluation in `tool.py`).
- Ported into: `ProgentDefense`.

## CaMeL

- Paper: Debenedetti et al., "Defeating Prompt Injections by Design",
  arXiv:2503.18813.
- Source: https://github.com/google-research/camel-prompt-injection
- Commit: `f083b6b396399d3b3c7f2ddaf613a5945eaf32d8`
- License: Apache-2.0 (see `third_party/camel/LICENSE`).
- Vendored: `third_party/camel/src_camel/` (`security_policy.py`,
  `capabilities/`). The full interpreter + quarantined-LLM pipeline is NOT
  vendored and NOT ported.
- Ported into: `CamelStyleDefense` (capability/data-flow *principle* only).
