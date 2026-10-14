# CLAUDE.md

`infuse` = INFUSE (formerly SecuredAgentBench), the packaged successor of `../secured-agent-bench` (legacy) and
`../infuse-bench` (stale snapshot). Work here.

Commands: `make install`, `make test` (no keys/Docker), `infuse --help`. Test with
`PYTHONPATH=. python -m pytest tests -q` if not installed.

Rules that keep the repo consistent (see docs/ARCHITECTURE.md "Where things are decided"):
- paths only via `infuse/paths.py`; surfaces only via `infuse/surfaces.py`; payload bytes only via
  `infuse/injection/assemble.py`; defenses/models only via `infuse/registry/`.
- `--strategy task_order` must keep matching the legacy injector (tests/test_resolver_equivalence.py).
- `TERMINAL_OUTPUT` is not an injection surface. Do not add runtime injection.
- Attack configs and task overlays must load with `strict=True`; run `infuse migrate-configs --write` after editing.
- Never commit results, figures or notebooks with outputs.
