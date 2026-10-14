"""
Daytona Environment
Executes bash commands in a Daytona sandbox (agent-native container runtime).
"""

from __future__ import annotations

import base64
import io
import logging
import os
import tarfile
import uuid
import inspect
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterable


@dataclass
class DaytonaEnvironmentConfig:
    """Configuration for Daytona sandbox execution."""

    # Auth/config (optional; SDK also supports env vars)
    api_key: str | None = None
    api_url: str | None = None
    target: str | None = None

    # Runtime
    image: str | None = None
    """Container image to use (if supported by the Daytona backend)."""

    cwd: str = "/work"
    """Working directory in which to execute commands."""

    env: dict[str, str] = field(default_factory=dict)
    """Environment variables to set (best effort; applied via shell prefix)."""

    timeout: int = 30
    """Timeout for executing commands in the sandbox (seconds)."""

    # Sync / seed content
    sync_dirs: list[tuple[str, str]] = field(default_factory=list)
    """List of (host_path, sandbox_path) directories to upload into the sandbox."""


class DaytonaEnvironment:
    """
    Executes bash commands in a Daytona sandbox.

    Expected interface (used by agents):
    - execute(command: str, cwd: str = "", timeout: Optional[int] = None) -> {"output": str, "returncode": int}
    - get_template_vars() -> dict
    - cleanup()
    """

    def __init__(
        self,
        *,
        config_class: type = DaytonaEnvironmentConfig,
        logger: logging.Logger | None = None,
        **kwargs,
    ):
        self.logger = logger or logging.getLogger("env.daytona")
        self.config = config_class(**kwargs)
        self.sandbox = None
        self.sandbox_id: str | None = None
        self._boot()

    def get_template_vars(self) -> dict[str, Any]:
        import platform

        return asdict(self.config) | platform.uname()._asdict() | os.environ

    def _boot(self) -> None:
        """
        Create sandbox and (optionally) upload initial directories.
        """
        try:
            from daytona import Daytona  # type: ignore
        except Exception as e:  # pragma: no cover
            raise RuntimeError(
                "Daytona SDK is not installed. Install with: pip install daytona"
            ) from e

        # Best-effort: some SDK versions expose DaytonaConfig, others take kwargs/env vars.
        daytona = None
        try:
            from daytona import DaytonaConfig  # type: ignore

            cfg_kwargs: dict[str, Any] = {}
            if self.config.api_key:
                cfg_kwargs["api_key"] = self.config.api_key
            if self.config.api_url:
                cfg_kwargs["api_url"] = self.config.api_url
            if self.config.target:
                cfg_kwargs["target"] = self.config.target
            cfg = DaytonaConfig(**cfg_kwargs) if cfg_kwargs else DaytonaConfig()
            daytona = Daytona(cfg)
        except Exception:
            # Fallback: let Daytona() pick up env vars.
            daytona = Daytona()

        sandbox_name = f"minisweagent-{uuid.uuid4().hex[:8]}"
        # Prefer capability detection over exception-based fallback: Daytona SDK signatures vary.
        create_kwargs: dict[str, Any] = {}
        try:
            sig = inspect.signature(daytona.create)  # type: ignore[arg-type]
            params = sig.parameters
            if "name" in params:
                create_kwargs["name"] = sandbox_name
            if self.config.image and "image" in params:
                create_kwargs["image"] = self.config.image
        except Exception:
            # If introspection fails, fall back to the broadest attempt and handle errors below.
            if self.config.image:
                create_kwargs["image"] = self.config.image
            create_kwargs["name"] = sandbox_name

        try:
            self.sandbox = daytona.create(**create_kwargs)
        except TypeError:
            # Final fallback for older SDKs that accept no kwargs at all.
            self.sandbox = daytona.create()
        except Exception as e:
            raise RuntimeError(f"Failed to create Daytona sandbox: {e}") from e

        self.sandbox_id = getattr(self.sandbox, "id", None) or getattr(self.sandbox, "sandbox_id", None)
        self.logger.info(f"Started Daytona sandbox {sandbox_name} ({self.sandbox_id or 'unknown-id'})")

        # Ensure working dir exists
        self.execute(f"mkdir -p {sh_quote(self.config.cwd)}", cwd="/")

        # Upload requested directories (best effort)
        for host_path, sandbox_path in self.config.sync_dirs:
            self._upload_dir(Path(host_path), sandbox_path)

        # Mirror Docker env behavior: if task data is available at /workspace/my_pc (read-only semantics),
        # ensure a writable copy exists under the working directory (/work/my_pc by default).
        # Many tasks/evaluators assume paths like "my_pc/taskX" relative to cwd.
        if any(dst.rstrip("/") == "/workspace/my_pc" for _, dst in self.config.sync_dirs):
            work_my_pc = str(Path(self.config.cwd) / "my_pc")
            self.execute(
                # If /workspace/my_pc exists and workdir copy is missing, create a writable copy.
                f"[ -d /workspace/my_pc ] && [ ! -d {sh_quote(work_my_pc)} ] && "
                f"cp -r /workspace/my_pc {sh_quote(self.config.cwd)} || true",
                cwd="/",
                timeout=max(self.config.timeout, 120),
            )

    def _upload_dir(self, host_path: Path, sandbox_path: str) -> None:
        """
        Upload a host directory into the sandbox.

        Implementation uses the Daytona filesystem API if available; otherwise raises.
        """
        host_path = host_path.resolve()
        if not host_path.exists():
            self.logger.warning(f"Daytona sync: host path does not exist: {host_path}")
            return

        # Prefer a tarball upload via fs.upload_file (fast, preserves perms reasonably)
        tar_bytes = _tar_gz_bytes(host_path)
        remote_tar = f"/tmp/{uuid.uuid4().hex}.tar.gz"
        self.execute(f"mkdir -p {sh_quote(sandbox_path)}", cwd="/")

        # Try Daytona fs API
        fs = getattr(self.sandbox, "fs", None)
        if fs and hasattr(fs, "upload_file"):
            try:
                # Daytona SDK expects upload_file(src, dst), where src can be bytes.
                fs.upload_file(tar_bytes, remote_tar)
                self.execute(
                    f"tar -xzf {sh_quote(remote_tar)} -C {sh_quote(sandbox_path)}",
                    cwd="/",
                    timeout=max(self.config.timeout, 120),
                )
                return
            except Exception as e:
                self.logger.warning(f"Daytona fs.upload_file failed, falling back to per-file upload: {e}")

        # Fallback: per-file upload via fs.upload_file if it exists and accepts bytes/str content
        if fs and hasattr(fs, "upload_file"):
            for rel in _iter_files(host_path):
                src = host_path / rel
                dst = str(Path(sandbox_path) / rel)
                self.execute(f"mkdir -p {sh_quote(str(Path(dst).parent))}", cwd="/")
                data = src.read_bytes()
                # Daytona SDK expects upload_file(src, dst), where src can be bytes.
                fs.upload_file(data, dst)
            return

        raise RuntimeError(
            "Daytona SDK filesystem upload is unavailable (expected sandbox.fs.upload_file). "
            "Please install/upgrade the Daytona Python SDK."
        )

    def execute(self, command: str, cwd: str = "", *, timeout: int | None = None) -> dict[str, Any]:
        """
        Execute a command in the Daytona sandbox and return {output, returncode}.
        """
        if not self.sandbox:
            raise RuntimeError("Daytona sandbox not initialized")

        cwd = cwd or self.config.cwd

        # Best-effort env injection: prefix with exports.
        env_prefix = ""
        if self.config.env:
            exports = " ".join(f"{k}={sh_quote(v)}" for k, v in self.config.env.items())
            env_prefix = f"export {exports}; "

        full_cmd = f"{env_prefix}{command}"

        # SDK compatibility: some versions expose sandbox.process.exec(), others sandbox.exec().
        proc = getattr(self.sandbox, "process", None)
        exec_fn = None
        if proc and hasattr(proc, "exec"):
            exec_fn = proc.exec
        elif hasattr(self.sandbox, "exec"):
            exec_fn = getattr(self.sandbox, "exec")
        if not exec_fn:
            raise RuntimeError("Daytona sandbox does not expose an exec method (expected process.exec() or exec())")

        try:
            resp = exec_fn(full_cmd, cwd=cwd, timeout=timeout or self.config.timeout)
        except TypeError:
            # Some SDKs may not support cwd/timeout kwargs
            resp = exec_fn(full_cmd)
        except Exception as e:
            raise RuntimeError(f"Daytona exec failed: {e}") from e

        # Normalize response
        output = getattr(resp, "stdout", None)
        if output is None:
            output = getattr(resp, "output", None)
        if output is None:
            output = getattr(resp, "result", "")
        if output is None:
            output = ""

        returncode = getattr(resp, "exit_code", None)
        if returncode is None:
            returncode = getattr(resp, "returncode", None)
        if returncode is None:
            returncode = 0

        return {"output": str(output), "returncode": int(returncode)}

    def cleanup(self) -> None:
        """
        Stop/delete the sandbox if supported by SDK (best effort).
        """
        sb = self.sandbox
        self.sandbox = None
        if not sb:
            return
        for method in ("delete", "stop", "close"):
            if hasattr(sb, method):
                try:
                    getattr(sb, method)()
                    return
                except Exception:
                    continue

    def __del__(self) -> None:  # pragma: no cover
        try:
            self.cleanup()
        except Exception:
            pass


def sh_quote(s: str) -> str:
    # Minimal shell quoting (single-quote safe)
    return "'" + s.replace("'", "'\"'\"'") + "'"


def _tar_gz_bytes(src_dir: Path) -> bytes:
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tf:
        tf.add(str(src_dir), arcname=".")
    return buf.getvalue()


def _iter_files(root: Path) -> Iterable[Path]:
    for p in root.rglob("*"):
        if p.is_file():
            yield p.relative_to(root)


