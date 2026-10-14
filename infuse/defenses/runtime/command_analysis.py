"""Best-effort static analysis of shell commands for privilege-control defenses.

The privilege-control defenses ported from Progent and CaMeL were designed for
agents that emit *structured tool calls* (``tool_name`` + typed ``kwargs``).
mini-swe-agent instead emits a single free-form **bash command** per step, so
before either policy can be enforced we decompose that command into a sequence
of tool-call-like primitives.

This is intentionally a heuristic analyzer, not a full bash parser: its job is
to surface the executables invoked and the security-relevant *sinks* a command
touches (network egress, file writes, reads of sensitive files) so a policy can
gate them.  It errs toward *over*-detection of sinks — a defense built on it is
free-to-deny, which is the safe direction for an injection benchmark.
"""

from __future__ import annotations

import re
import shlex
from dataclasses import dataclass, field

# Operators that separate one command invocation from the next.
_SEGMENT_SPLIT = re.compile(r"\|\||&&|\||;|\n")

# Leading tokens that are not the "real" executable of a segment.
_ASSIGNMENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")
_WRAPPERS = {"sudo", "env", "nohup", "time", "exec", "command", "builtin", "\\"}

# Executables that move data off the machine (egress sinks).
NETWORK_BINARIES = {
    "curl", "wget", "nc", "ncat", "netcat", "telnet", "ssh", "scp", "sftp",
    "ftp", "rsync", "socket", "socat", "http", "https",
}

# Executables that can write / mutate the filesystem.
WRITE_BINARIES = {
    "tee", "cp", "mv", "rm", "dd", "truncate", "install", "ln", "mkdir",
    "rmdir", "touch", "chmod", "chown", "shred", "sed",  # sed -i
}

# Paths that should never be read/written by a task unless explicitly granted.
SENSITIVE_PATHS = (
    "/etc/passwd", "/etc/shadow", "~/.ssh", "/.ssh/", "id_rsa", ".aws/",
    ".git-credentials", ".netrc", "/root/", ".env", "credentials",
    "authorized_keys",
)

# Host regex — matches http(s)://host, user@host, or bare host:port.
_URL_HOST = re.compile(r"https?://([^/\s'\"]+)", re.I)
_SCP_HOST = re.compile(r"[\w.-]+@([\w.-]+):")
_BARE_HOST = re.compile(r"\b((?:[\w-]+\.)+[a-z]{2,})(?::\d+)?\b", re.I)


@dataclass
class Invocation:
    """One executable invocation inside a (possibly compound) shell command."""

    executable: str
    args: str  # the raw argument string following the executable
    raw: str   # the full segment as written


@dataclass
class CommandAnalysis:
    """Structured, security-relevant view of a whole shell command."""

    invocations: list[Invocation] = field(default_factory=list)
    network_egress: bool = False
    egress_hosts: set[str] = field(default_factory=set)
    file_writes: bool = False
    write_targets: set[str] = field(default_factory=set)
    sensitive_access: set[str] = field(default_factory=set)

    @property
    def executables(self) -> list[str]:
        return [inv.executable for inv in self.invocations]


def _tokenize(segment: str) -> list[str]:
    try:
        return shlex.split(segment, comments=False, posix=True)
    except ValueError:
        # Unbalanced quotes etc. — fall back to whitespace splitting.
        return segment.split()


def _leading_executable(tokens: list[str]) -> tuple[str, list[str]]:
    """Strip env assignments / wrappers and return (executable, remaining args)."""
    i = 0
    while i < len(tokens):
        tok = tokens[i]
        if _ASSIGNMENT.match(tok) or tok in _WRAPPERS:
            i += 1
            continue
        break
    if i >= len(tokens):
        return "", []
    exe = tokens[i]
    # Normalize an absolute/relative path to its basename (/usr/bin/curl -> curl).
    exe_base = exe.rsplit("/", 1)[-1]
    return exe_base, tokens[i + 1:]


def _extract_hosts(text: str) -> set[str]:
    hosts: set[str] = set()
    hosts.update(m.group(1) for m in _URL_HOST.finditer(text))
    hosts.update(m.group(1) for m in _SCP_HOST.finditer(text))
    hosts.update(m.group(1) for m in _BARE_HOST.finditer(text))
    # Drop obvious local references.
    return {h for h in hosts if h not in {"localhost", "127.0.0.1", "0.0.0.0"}}


def _looks_like_egress(exe: str, args: str, raw: str) -> bool:
    if exe in NETWORK_BINARIES:
        return True
    # python/perl/ruby one-liners that open sockets or POST.
    if exe in {"python", "python3", "perl", "ruby", "node"}:
        if re.search(r"requests\.(post|get|put)|urllib|socket|http\.client|fetch\(", raw):
            return True
    if exe == "git" and re.search(r"\b(push|clone|pull|fetch|remote)\b", args):
        return "://" in raw or "@" in raw
    return False


def analyze_command(command: str) -> CommandAnalysis:
    """Decompose a shell command into invocations + security-relevant sinks."""
    analysis = CommandAnalysis()
    if not command or not command.strip():
        return analysis

    # Split on control operators; redirections are handled per-segment below.
    segments = [s.strip() for s in _SEGMENT_SPLIT.split(command) if s.strip()]

    for seg in segments:
        tokens = _tokenize(seg)
        if not tokens:
            continue
        exe, rest = _leading_executable(tokens)
        if not exe:
            continue
        args = " ".join(rest)
        analysis.invocations.append(Invocation(executable=exe, args=args, raw=seg))

        # --- network egress ---
        if _looks_like_egress(exe, args, seg):
            analysis.network_egress = True
            analysis.egress_hosts |= _extract_hosts(seg)

        # --- file writes ---
        if exe in WRITE_BINARIES or (exe == "sed" and "-i" in rest):
            analysis.file_writes = True
            analysis.write_targets |= {t for t in rest if not t.startswith("-")}
        # Output redirection ( > , >> ) writes regardless of executable.
        for m in re.finditer(r">>?\s*([^\s>|&;]+)", seg):
            analysis.file_writes = True
            analysis.write_targets.add(m.group(1))

        # --- sensitive-path access ---
        low = seg.lower()
        for sp in SENSITIVE_PATHS:
            if sp.lower() in low:
                analysis.sensitive_access.add(sp)

    return analysis
