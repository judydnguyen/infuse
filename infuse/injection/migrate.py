"""Normalise attack configs and task overlays to the strict schema (text-level, comment-preserving).

What it does
  attacks/*/config.toml
    * drops retired names (TERMINAL_OUTPUT, CONFIG_WRITE, ...) from ``primary = [...]`` / ``fallback = [...]``
    * removes legacy root-level flat keys (``type``, ``attack_id``, ``surfaces``, ``payload`` outside [attack])
    * sets ``[attack].id`` to the directory number (attack_31..35 shipped with id 21..25)
  tasks/*/environment/overlays/benign.toml
    * deletes whole ``[surfaces.<RETIRED>]`` blocks (with their leading comment lines)

Dry-run by default; ``--write`` applies. Resolution targets are unaffected (the retired
entries never matched anything), which ``tests/test_resolver_equivalence.py`` guards.
"""
from __future__ import annotations

import difflib
import re
from pathlib import Path

from infuse import paths
from infuse.surfaces import RETIRED_INJECTION_SURFACES, InjectionSurface

_VALID = {s.value for s in InjectionSurface}
_LIST_LINE = re.compile(r"^(\s*)(primary|fallback)(\s*=\s*)\[(.*?)\](.*)$")
_HEADER = re.compile(r"^\[([^\]]+)\]\s*$")


def _clean_list(items: str) -> str:
    names = [x.strip().strip("'\"") for x in items.split(",") if x.strip()]
    kept = [n for n in names if n in _VALID]
    return ", ".join(f"'{n}'" for n in kept)


def migrate_attack_text(text: str, dir_id: str | None = None) -> str:
    out: list[str] = []
    in_root = True
    in_attack_table = False  # before the first [table] header, where legacy flat keys live
    skipping_multiline = False
    for line in text.splitlines(keepends=True):
        h = _HEADER.match(line)
        if h:
            in_root = False
            in_attack_table = h.group(1) == "attack"
        elif in_attack_table and dir_id is not None:
            mid = re.match(r'^(\s*id\s*=\s*)"[^"]*"(.*)$', line.rstrip("\n"))
            if mid and f'"{dir_id}"' not in line:
                line = f'{mid.group(1)}"{dir_id}"{mid.group(2)}\n'
        if in_root:
            if skipping_multiline:
                if line.strip() == '"""':
                    skipping_multiline = False
                continue
            m = re.match(r'^\s*(type|attack_id|surfaces|payload)\s*=\s*(.*)$', line)
            if m:
                if m.group(2).strip() == '"""':
                    skipping_multiline = True
                continue
            if line.strip().startswith("# Flat keys"):
                continue
        m = _LIST_LINE.match(line.rstrip("\n"))
        if m:
            indent, key, eq, items, rest = m.groups()
            line = f"{indent}{key}{eq}[{_clean_list(items)}]{rest}\n"
        out.append(line)
    return "".join(out)


def migrate_overlay_text(text: str) -> str:
    lines = text.splitlines(keepends=True)
    out: list[str] = []
    i = 0
    while i < len(lines):
        m = _HEADER.match(lines[i])
        if m and m.group(1).startswith("surfaces.") and m.group(1).split(".", 1)[1] in RETIRED_INJECTION_SURFACES:
            # drop immediately preceding comment/blank lines that introduced this block
            while out and (out[-1].lstrip().startswith("#") or not out[-1].strip()):
                out.pop()
            i += 1
            while i < len(lines) and not _HEADER.match(lines[i]) and not _introduces_next_block(lines, i):
                i += 1
            if out and out[-1].strip():
                out.append("\n")
            continue
        out.append(lines[i])
        i += 1
    return "".join(out)


def _introduces_next_block(lines: list[str], i: int) -> bool:
    """True if lines[i:] is only comments/blank lines up to the next [header] (they belong to that header)."""
    if not lines[i].lstrip().startswith("#"):
        return False
    j = i
    while j < len(lines) and (lines[j].lstrip().startswith("#") or not lines[j].strip()):
        j += 1
    return j < len(lines) and bool(_HEADER.match(lines[j]))


def _targets() -> list[tuple[Path, str]]:
    items: list[tuple[Path, str]] = []
    for p in sorted(paths.ATTACKS_DIR.glob("attack_*/config.toml")):
        items.append((p, "attack"))
    for p in sorted(paths.TASKS_DIR.glob("task_*/environment/overlays/benign.toml")):
        items.append((p, "overlay"))
    return items


def run(write: bool = False, verbose: bool = True) -> int:
    """Return the number of files that change (or changed)."""
    changed = 0
    for p, kind in _targets():
        old = p.read_text(encoding="utf-8")
        new = migrate_attack_text(old, p.parent.name.split("_", 1)[1]) if kind == "attack" else migrate_overlay_text(old)
        if new == old:
            continue
        changed += 1
        if verbose:
            rel = p.relative_to(paths.REPO_ROOT)
            diff = difflib.unified_diff(old.splitlines(), new.splitlines(), str(rel), str(rel), lineterm="", n=1)
            print("\n".join(diff))
        if write:
            p.write_text(new, encoding="utf-8")
    if verbose:
        print(f"\n{changed} file(s) {'rewritten' if write else 'would change (use --write)'}")
    return changed


if __name__ == "__main__":  # pragma: no cover
    import sys
    run(write="--write" in sys.argv)
