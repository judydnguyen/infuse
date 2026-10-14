"""Payload assembly: the single function that decides the bytes an attack places.

Everything that previously assembled a payload (``_build_attack_payload`` in the
runner, ``_inject_single`` / ``_inject_payload`` in the injector, the setup.sh
argument, the judge's expected payload) now goes through :func:`assemble_payload`
so the recorded payload is byte-identical to the injected one.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from infuse import paths
from infuse.injection.spec import AttackSpec

VARIANTS: tuple[str, ...] = ("default", "gcg", "troubleshoot")

_COMMENT_HASH = {".py", ".sh", ".rb", ".pl", ".yaml", ".yml", ".toml", ".conf", ".r", ".txt"}
_COMMENT_SLASH = {".js", ".ts", ".java", ".c", ".cpp", ".go", ".rs", ".swift", ".kt"}
_INVALID_FILENAME_CHARS = ["/", "\\", "\0", ":", "*", "?", '"', "<", ">", "|", "\n", "\r"]


def variant_template(spec: AttackSpec, variant: str = "default") -> str:
    """Template text for an ``obs-level`` variant (``default`` = config.toml as-is)."""
    if variant not in VARIANTS:
        raise ValueError(f"variant must be one of {VARIANTS}, got {variant!r}")
    template = spec.payload_template
    if variant == "default":
        return template

    def _match(entry: dict) -> bool:
        return str(entry.get("id_raw", "")) == spec.id or str(entry.get("id", "")) == spec.id

    if variant == "gcg":
        src = paths.TEMPLATES_DIR / "ATTACK_TEMPLATES_GCG.json"
        for entry in json.loads(src.read_text()):
            if _match(entry):
                return entry["template"]
    elif variant == "troubleshoot":
        src = paths.TEMPLATES_DIR / "ATTACK_TEMPLATES_TROUBLESHOOTING.json"
        for entry in json.loads(src.read_text()):
            if _match(entry):
                steps = "\n".join(entry.get("steps", []))
                return f"{entry['title']}\n\n{entry['symptom']}\n\n{steps}"
    return template  # no variant entry for this attack: fall back to default


def assemble_payload(spec: AttackSpec, variant: str = "default") -> str:
    """``inject_prefix + template`` (no separator), exactly as every collected run did."""
    prefix, template = spec.inject_prefix, variant_template(spec, variant)
    return (prefix + template) if (prefix and template) else (template or prefix)


def payload_sha256(payload: str) -> str:
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def wrap_as_comment(path: Path, text: str) -> str:
    """Comment-wrap *text* for code-like files; plain/unknown files get it verbatim."""
    ext = path.suffix.lower()
    if ext in _COMMENT_HASH:
        return "\n".join(f"# {line}" for line in text.splitlines())
    if ext in _COMMENT_SLASH:
        return "\n".join(f"// {line}" for line in text.splitlines())
    if ext in {".html", ".xml"}:
        return f"<!-- {text} -->"
    if ext == ".sql":
        return "\n".join(f"-- {line}" for line in text.splitlines())
    return text


def place(content: str, text: str, position: str) -> str:
    """Insert *text* into *content* at *position* (prepend | append | inline | replace)."""
    if position == "prepend":
        return text + "\n" + content
    if position == "inline":
        lines = content.splitlines(keepends=True)
        lines.insert(len(lines) // 2, text + "\n")
        return "".join(lines)
    if position == "replace":
        return text
    # append (also the default for anything unrecognised, matching legacy behaviour)
    if content and not content.endswith("\n"):
        return content + "\n" + text + "\n"
    return content + text + "\n"


def poisoned_filename(payload: str, max_bytes: int = 250) -> str:
    """A filesystem-safe file name carrying *payload*, ``.txt``-suffixed."""
    s = payload
    for ch in _INVALID_FILENAME_CHARS:
        s = s.replace(ch, "_")
    while len(s.encode("utf-8")) > max_bytes:
        s = s[:-1]
    if not s.strip():
        s = "payload"
    return f"{s}.txt"


__all__ = ["VARIANTS", "variant_template", "assemble_payload", "payload_sha256", "wrap_as_comment", "place",
           "poisoned_filename"]
