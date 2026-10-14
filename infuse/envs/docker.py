"""
Docker Environment
Executes bash commands in a Docker container with proper isolation and cleanup.
"""

import base64
import logging
import os
import shlex
import subprocess
import uuid
from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class DockerEnvironmentConfig:
    """Configuration for Docker environment execution."""
    image: str
    """Docker image to use."""
    cwd: str = "/"
    """Working directory in which to execute commands."""
    env: dict[str, str] = field(default_factory=dict)
    """Environment variables to set in the container."""
    forward_env: list[str] = field(default_factory=list)
    """Environment variables to forward to the container.
    Variables are only forwarded if they are set in the host environment.
    In case of conflict with `env`, the `env` variables take precedence.
    """
    volumes: list[str] = field(default_factory=list)
    """Volume mounts in the format 'host_path:container_path' or 'host_path:container_path:ro'."""
    timeout: int = 30
    """Timeout for executing commands in the container."""
    executable: str = os.getenv("MSWEA_DOCKER_EXECUTABLE", "docker")
    """Path to the docker/container executable."""
    run_args: list[str] = field(default_factory=lambda: ["--rm"])
    """Additional arguments to pass to the docker/container executable.
    Default is ["--rm"], which removes the container after it exits.
    """
    container_timeout: str = "2h"
    """Max duration to keep container running. Uses the same format as the sleep command."""
    pull_timeout: int = 120
    """Timeout in seconds for pulling images."""
    attack_config: dict | None = None
    """Attack configuration for runtime injection. Injected after files are copied to /work."""
    attack_target_file: str | None = None
    """Specific file to inject attack into (relative path). If None, uses benign overlay to determine target."""


class DockerEnvironment:
    """Executes bash commands in a Docker container using direct docker commands."""
    
    def __init__(self, *, config_class: type = DockerEnvironmentConfig, logger: logging.Logger | None = None, **kwargs):
        """
        Initialize Docker environment.
        
        Args:
            config_class: Configuration class to use
            logger: Optional logger instance
            **kwargs: Configuration parameters (image, cwd, volumes, etc.)
        """
        self.logger = logger or logging.getLogger("env.docker")
        self.container_id: str | None = None
        self.config = config_class(**kwargs)
        self._start_container()

    def get_template_vars(self) -> dict[str, Any]:
        """
        Get template variables for rendering templates.
        
        Returns:
            Dictionary of template variables (config, system info)
        """
        import platform
        return asdict(self.config) | platform.uname()._asdict()

    def _start_container(self):
        """Start the Docker container and return the container ID."""
        container_name = f"minisweagent-{uuid.uuid4().hex[:8]}"
        cmd = [
            self.config.executable,
            "run",
            "-d",
            "--name",
            container_name,
            "-w",
            self.config.cwd,
        ]
        # Add volume mounts
        for volume in self.config.volumes:
            cmd.extend(["-v", volume])
        cmd.extend([
            *self.config.run_args,
            self.config.image,
            "sleep",
            self.config.container_timeout,
        ])
        self.logger.debug(f"Starting container with command: {shlex.join(cmd)}")
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=self.config.pull_timeout,  # docker pull might take a while
            check=True,
        )
        self.logger.info(f"Started container {container_name} with ID {result.stdout.strip()}")
        self.container_id = result.stdout.strip()

        # Copy task files from /workspace/my_pc to /work/my_pc immediately after container starts
        # This ensures files are available in writable location before any commands are run
        self._copy_task_files()

        # NOTE: Attack injection is now done at build time (in Docker image), not at runtime.
        # The _inject_attack_payload() method is kept for backward compatibility but not called.
        self._injected_file = None

    def _inject_attack_payload(self) -> None:
        """
        Inject attack payload into target file inside the container.

        This is called AFTER files are copied to /work,
        ensuring the attack payload is present when the agent reads files.
        """
        if not self.config.attack_config:
            return

        attack = self.config.attack_config.get("attack", {})
        payload_config = attack.get("payload", {})
        payload = payload_config.get("template", "")

        if not payload:
            self.logger.warning("No attack payload template found in config")
            return

        # Determine target file
        target_file = self.config.attack_target_file
        if not target_file:
            # Try to find target from attack config's target patterns
            target_config = attack.get("target", {})
            file_patterns = target_config.get("file_patterns", [])

            if file_patterns:
                # Search in the correct base directory based on config.cwd
                search_dir = self.config.cwd if self.config.cwd != "/" else "/work"
                for pattern in file_patterns:
                    find_cmd = f"find {search_dir} -name '{pattern}' -type f 2>/dev/null | head -1"
                    find_full_cmd = [
                        self.config.executable, "exec", self.container_id,
                        "bash", "-c", find_cmd
                    ]
                    try:
                        result = subprocess.run(find_full_cmd, capture_output=True, text=True, timeout=5)
                        if result.returncode == 0 and result.stdout.strip():
                            target_file = result.stdout.strip()
                            break
                    except Exception:
                        continue

        if not target_file:
            self.logger.warning("No target file found for attack injection")
            return

        # Ensure target_file is an absolute path based on config.cwd
        # When data_in_image=True, cwd is /app; otherwise /work
        if not target_file.startswith("/"):
            base_dir = self.config.cwd if self.config.cwd != "/" else "/work"
            target_file = f"{base_dir}/{target_file}"

        # Get injection position and prefix
        target_config = attack.get("target", {})
        inject_position = target_config.get("inject_position", "append")
        inject_prefix = target_config.get("inject_prefix", "")

        # Apply prefix if provided
        if inject_prefix:
            payload = f"{inject_prefix}\n{payload}"

        # Escape payload for shell - use base64 encoding to handle special chars
        payload_b64 = base64.b64encode(payload.encode('utf-8')).decode('ascii')

        # Build injection command based on position
        if inject_position == "prepend":
            inject_cmd = (
                f"PAYLOAD=$(echo '{payload_b64}' | base64 -d) && "
                f"ORIG=$(cat '{target_file}') && "
                f"echo -e \"$PAYLOAD\\n$ORIG\" > '{target_file}'"
            )
        elif inject_position == "replace":
            inject_cmd = f"echo '{payload_b64}' | base64 -d > '{target_file}'"
        else:
            # Append (default): add newline + payload to end
            inject_cmd = f"echo '{payload_b64}' | base64 -d >> '{target_file}'"

        # Create backup before injection (for later revert)
        backup_cmd = f"cp '{target_file}' '{target_file}.attack_backup'"
        backup_full_cmd = [
            self.config.executable, "exec", self.container_id,
            "bash", "-c", backup_cmd
        ]
        try:
            subprocess.run(backup_full_cmd, capture_output=True, timeout=5, check=False)
        except Exception:
            pass  # Best effort backup

        # Execute injection inside container
        inject_full_cmd = [
            self.config.executable, "exec", self.container_id,
            "bash", "-c", inject_cmd
        ]

        try:
            result = subprocess.run(inject_full_cmd, capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                self._injected_file = target_file  # Track for revert
                self.logger.info(f"Injected attack payload ({inject_position}) into {target_file}")
            else:
                self.logger.warning(f"Failed to inject attack payload: {result.stderr}")
        except Exception as e:
            self.logger.warning(f"Error injecting attack payload: {e}")

    def revert_attack_injection(self) -> bool:
        """
        Revert attack injection by restoring from backup.

        Call this before evaluation to ensure tests run against
        the agent's actual changes, not the injected payload.

        Returns:
            True if revert succeeded, False otherwise
        """
        if not self.container_id:
            return False

        injected_file = getattr(self, '_injected_file', None)
        if not injected_file:
            self.logger.debug("No attack injection to revert")
            return True

        backup_file = f"{injected_file}.attack_backup"
        revert_cmd = f"[ -f '{backup_file}' ] && mv '{backup_file}' '{injected_file}'"
        revert_full_cmd = [
            self.config.executable, "exec", self.container_id,
            "bash", "-c", revert_cmd
        ]

        try:
            result = subprocess.run(revert_full_cmd, capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                self.logger.info(f"Reverted attack injection in {injected_file}")
                self._injected_file = None
                return True
            else:
                self.logger.warning(f"Failed to revert attack injection: {result.stderr}")
                return False
        except Exception as e:
            self.logger.warning(f"Error reverting attack injection: {e}")
            return False

    def _copy_task_files(self):
        """
        Copy task files to /work once per container.

        Handles two scenarios:
        1. Legacy: /workspace/my_pc exists (mounted from host) -> copy to /work/my_pc
        2. New: /app exists with files (from Docker image COPY) -> copy to /work

        This allows agent to work with writable copies instead of read-only originals.
        """
        if not self.container_id:
            return

        # Track if we've copied task files (one-time setup per container)
        if not hasattr(self, '_files_copied'):
            self._files_copied = False

        if self._files_copied:
            return

        # Try copying from /workspace/my_pc (legacy mount) or /app (data in image)
        # Priority: /app (if has files other than __pycache__), then /workspace/my_pc
        copy_cmd = '''
if [ -d /app ] && [ "$(ls -A /app 2>/dev/null | grep -v __pycache__ | head -1)" ]; then
    # Data is in Docker image at /app - copy all contents to /work
    cp -r /app/* /work/ 2>/dev/null || true
    echo "copied_from_app"
elif [ -d /workspace/my_pc ]; then
    # Legacy: data mounted from host
    cp -r /workspace/my_pc /work/ 2>/dev/null || true
    echo "copied_from_my_pc"
fi
'''
        copy_full_cmd = [
            self.config.executable, "exec", "-w", "/work",
            self.container_id, "bash", "-c", copy_cmd
        ]
        try:
            result = subprocess.run(copy_full_cmd, capture_output=True, timeout=30, check=False)
            output = result.stdout.decode().strip() if result.stdout else ""
            if "copied_from_app" in output:
                self._files_copied = True
                self.logger.info("✓ Copied task files from /app to /work")
            elif "copied_from_my_pc" in output:
                self._files_copied = True
                self.logger.info("✓ Copied task files from /workspace/my_pc to /work/my_pc")
            else:
                self.logger.debug(f"No files to copy (output: {output})")
        except Exception as e:
            self.logger.debug(f"Could not copy task files: {e}")

    def execute(self, command: str, cwd: str = "", *, timeout: int | None = None) -> dict[str, Any]:
        """
        Execute a command in the Docker container and return the result as a dict.
        
        Args:
            command: Bash command to execute
            cwd: Working directory (overrides config.cwd if provided)
            timeout: Command timeout in seconds (overrides config.timeout if provided)
            
        Returns:
            Dictionary with 'output' (stdout) and 'returncode' keys
        """
        cwd = cwd or self.config.cwd
        assert self.container_id, "Container not started"
        
        # Ensure task files are copied (this will only copy once due to _files_copied flag)
        self._copy_task_files()

        cmd = [self.config.executable, "exec", "-w", cwd]
        for key in self.config.forward_env:
            if (value := os.getenv(key)) is not None:
                cmd.extend(["-e", f"{key}={value}"])
        for key, value in self.config.env.items():
            cmd.extend(["-e", f"{key}={value}"])
        cmd.extend([self.container_id, "bash", "-lc", command])

        result = subprocess.run(
            cmd,
            text=True,
            timeout=timeout or self.config.timeout,
            encoding="utf-8",
            errors="replace",
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        return {"output": result.stdout, "returncode": result.returncode}

    def cleanup(self):
        """Stop and remove the Docker container synchronously."""
        if getattr(self, "container_id", None) is not None:  # if init fails early, container_id might not be set
            container_id = self.container_id
            self.container_id = None  # Clear to prevent double cleanup
            try:
                # Stop container first (graceful shutdown)
                stop_cmd = [self.config.executable, "stop", "-t", "10", container_id]
                subprocess.run(stop_cmd, capture_output=True, timeout=15, check=False)
            except Exception:
                pass  # Ignore stop errors, will force remove
            
            try:
                # Force remove container (cleans up all files)
                rm_cmd = [self.config.executable, "rm", "-f", container_id]
                result = subprocess.run(rm_cmd, capture_output=True, timeout=15, check=False)
                if result.returncode == 0:
                    self.logger.info(f"Cleaned up container {container_id}")
                else:
                    self.logger.warning(f"Failed to remove container {container_id}: {result.stderr.decode()}")
            except Exception as e:
                self.logger.warning(f"Error during container cleanup: {e}")

    def __del__(self):
        """Cleanup container when object is destroyed."""
        self.cleanup()
