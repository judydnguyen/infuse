"""
Environment Materializer for test_tasks structure.

This module handles:
1. Building Docker images from task-specific Dockerfiles
2. Populating environment from test_tasks/task_X/environment/app/
3. Applying attack injections by manipulating files directly (pre-execution)
"""

import shlex
import shutil
import subprocess
import logging
import sys
from pathlib import Path
from typing import Optional, Dict, Any, List, TYPE_CHECKING

if TYPE_CHECKING:
    from infuse.tasks.task_suite import ExecutionTrace
try:
    import tomllib as tomli  # Python 3.11+
except ImportError:
    try:
        import tomli  # Fallback: tomli library
    except ImportError:
        raise ImportError("Need tomllib (Python 3.11+) or tomli library")

logger = logging.getLogger(__name__)


class TestTaskMaterializer:
    """Materializes environments from test_tasks structure."""
    
    def __init__(self, tasks_root: Path):
        """
        Initialize the materializer.
        
        Args:
            tasks_root: Root directory containing test_tasks (e.g., /path/to/test_tasks)
        """
        self.tasks_root = Path(tasks_root)
        self._last_attacked_files = []
        self._last_injection_record = None
        self._last_attacked_files: List[Path] = []
        if not self.tasks_root.exists():
            raise ValueError(f"Tasks root does not exist: {tasks_root}")
    
    def load_task_config(self, task_id: str) -> Dict[str, Any]:
        """
        Load task configuration from task.toml.
        
        Args:
            task_id: Task identifier (e.g., "task_1")
            
        Returns:
            Dictionary with task configuration
        """
        task_dir = self.tasks_root / task_id
        task_toml = task_dir / "task.toml"
        
        if not task_toml.exists():
            raise FileNotFoundError(f"Task config not found: {task_toml}")
        
        with open(task_toml, "rb") as f:
            config = tomli.load(f)  # type: ignore
        
        return config
    
    def load_benign_overlay(self, task_id: str) -> Dict[str, Any]:
        """
        Load benign overlay configuration.
        
        Args:
            task_id: Task identifier
            
        Returns:
            Dictionary with benign overlay configuration
        """
        overlay_path = self.tasks_root / task_id / "environment" / "overlays" / "benign.toml"
        
        if not overlay_path.exists():
            logger.warning(f"Benign overlay not found: {overlay_path}, using empty overlay")
            return {"overlay": {"type": "benign"}, "surfaces": {}}
        
        with open(overlay_path, "rb") as f:
            overlay = tomli.load(f)  # type: ignore
        
        return overlay
    
    def build_docker_image(
        self,
        task_id: str,
        image_name: Optional[str] = None,
        attack_config: Optional[Dict[str, Any]] = None,
        attack_dir_abs: Optional[str] = None,
        resolution_strategy: str = "task_order",
        payload_variant: str = "default",
    ) -> str:
        """
        Build Docker image from task-specific Dockerfile with data already populated.

        The build process:
        1. If environment/setup.sh exists, runs it first (cwd=task_dir). Optional
           args can be set in task.toml as [environment] setup_args = ["arg1", "arg2"].
        2. Copies files from environment/app/ to a temporary build context
        3. Applies attack injection if provided
        4. Builds Docker image with files already included

        Args:
            task_id: Task identifier
            image_name: Optional custom image name (defaults to task-specific name)
            attack_config: Optional attack configuration for injection

        Returns:
            Docker image name/tag
        """
        import tempfile
        
        task_dir = self.tasks_root / task_id
        dockerfile_path = task_dir / "environment" / "Dockerfile"
        
        if not dockerfile_path.exists():
            raise FileNotFoundError(f"Dockerfile not found: {dockerfile_path}")
        
        # Load task config to get image name if not provided
        if image_name is None:
            config = self.load_task_config(task_id)
            env_config = config.get("environment", {})
            image_name = env_config.get("docker_image", f"{task_id}:latest")
        
        # NOTE: setup.sh is now handled by the runner (run_single_minisweagent.py)
        # before calling build_docker_image, to avoid double execution and
        # ensure cleanup runs properly via the runner's finally block.

        # Create temporary build context with populated data
        with tempfile.TemporaryDirectory(prefix=f"task_{task_id}_build_") as temp_build_dir:
            temp_build_path = Path(temp_build_dir)
            
            # Copy Dockerfile to temp directory
            temp_dockerfile = temp_build_path / "Dockerfile"
            shutil.copy2(dockerfile_path, temp_dockerfile)
            
            # Copy app/ directory to temp build context
            app_dir = task_dir / "environment" / "app"
            if app_dir.exists():
                temp_app_dir = temp_build_path / "app"
                shutil.copytree(app_dir, temp_app_dir)
                logger.info(f"Copied app files to build context: {temp_app_dir}")

            # Copy tests/ directory to temp build context (for evaluation)
            tests_dir = task_dir / "tests"
            if tests_dir.exists():
                temp_tests_dir = temp_build_path / "tests"
                shutil.copytree(tests_dir, temp_tests_dir)
                logger.info(f"Copied tests to build context: {temp_tests_dir}")

                # Modify Dockerfile to also copy tests
                with open(temp_dockerfile, "a") as f:
                    f.write("\n# Copy test scripts for evaluation\n")
                    f.write("COPY tests /tests\n")
                    f.write("RUN chmod +x /tests/*.sh 2>/dev/null || true\n")

            else:
                # Create empty app directory if it doesn't exist
                temp_app_dir = temp_build_path / "app"
                temp_app_dir.mkdir()

            # Phase 1: Build Docker image from temp build context (clean, no attack yet)
            logger.info(f"Building Docker image {image_name} from {dockerfile_path}")

            # cmd = [
            #     "docker", "build",
            #     "-f", str(temp_dockerfile),
            #     "-t", image_name,
            #     str(temp_build_path)
            # ]
            
            if attack_dir_abs:
                logger.info(f"Inlining attack setup into Dockerfile: {attack_dir_abs}")
                setup_sh = Path(attack_dir_abs) / "setup.sh"
                if setup_sh.exists():
                    setup_content = setup_sh.read_text()
                    # Strip shebang and the WORKDIR/cd boilerplate — replace with hardcoded /app
                    lines = []
                    for line in setup_content.splitlines():
                        if line.startswith("#!"):
                            continue
                        if 'WORKDIR=' in line and ':-' in line:
                            lines.append('WORKDIR=/app')
                            continue
                        if line.strip().startswith('mkdir -p "$WORKDIR"') or line.strip() == 'cd "$(dirname "$0")"':
                            continue
                        lines.append(line)
                    inline_script = "\n".join(lines)
                    # Write the script to a temp file in the build context
                    setup_tmp = temp_build_path / "_attack_setup.sh"
                    setup_tmp.write_text(inline_script)
                    with open(temp_dockerfile, "a") as f:
                        f.write("\nCOPY _attack_setup.sh /tmp/_attack_setup.sh\n")
                        f.write("RUN bash /tmp/_attack_setup.sh\n")
                    print("Inlined attack setup.sh into Dockerfile", file=sys.stderr)

            cmd = [
                "docker", "build",
                "-f", str(temp_dockerfile),
                "-t", image_name,
                str(temp_build_path)
            ]
            
            print(f"Running Docker build command: {' '.join(cmd)}", file=sys.stderr)
            print(f"Content of Dockerfile:\n{temp_dockerfile.read_text()}", file=sys.stderr)
            
            try:
                subprocess.run(
                    cmd,
                    stdout=sys.stderr,
                    stderr=sys.stderr,
                    check=True
                )
                logger.info(f"Successfully built image {image_name}")
            except subprocess.CalledProcessError as e:
                logger.error(f"Failed to build Docker image (exit {e.returncode})")
                raise

            # Phase 2: inject the attack into the build context, then patch the image.
            self._last_attacked_files = []
            self._last_injection_record = None
            if attack_config:
                from infuse.injection import AttackSpec, TaskSurfaces, inject
                spec = AttackSpec.from_dict(attack_config, source=None, strict=False)
                task_surfaces = TaskSurfaces.from_dict(self.load_benign_overlay(task_id), task_id=task_id, strict=False)
                record = inject(spec, task_surfaces, temp_app_dir,
                                strategy=resolution_strategy, variant=payload_variant,
                                payload=attack_config.get("_assembled_payload"))
                self._last_injection_record = record
                attacked_files = [temp_app_dir / f for f in record.written_files]
                if attacked_files:
                    container_name = f"attack_inject_{task_id}_{id(temp_build_path)}"
                    try:
                        subprocess.run(
                            ["docker", "create", "--name", container_name, image_name],
                            check=True, capture_output=True, text=True
                        )
                        for attacked_file in attacked_files:
                            rel = attacked_file.relative_to(temp_app_dir)
                            self._last_attacked_files.append(rel)
                            subprocess.run(
                                ["docker", "cp", str(attacked_file), f"{container_name}:/app/{rel}"],
                                check=True, capture_output=True, text=True
                            )
                            logger.info(f"Applied attack injection post-build: {rel}")
                        subprocess.run(
                            ["docker", "commit", container_name, image_name],
                            check=True, capture_output=True, text=True
                        )
                        logger.info(f"Patched Docker image {image_name} with {len(attacked_files)} attack file(s)")
                    except subprocess.CalledProcessError as e:
                        logger.error(f"Failed to patch Docker image with attack: {e.stderr}")
                        raise
                    finally:
                        subprocess.run(["docker", "rm", "-f", container_name], capture_output=True)

        return image_name
    
    def run_docker(
        self,
        image_name: str,
        python_args: List[str],
        attack_dir_abs: Optional[str] = None,
        extra_run_args: Optional[List[str]] = None,
    ) -> subprocess.CompletedProcess:
        """Run a Docker container with the built image.

        Ensures /work exists, optionally runs /attack/setup.sh if an attack
        directory is mounted, then executes the given Python command.

        Args:
            image_name: Docker image to run
            python_args: Python command + args (e.g. ["python", "-m", "runners.run_single", ...])
            attack_dir_abs: Absolute path to attack directory on the host (mounted at /attack:ro)
            extra_run_args: Additional docker run flags (defaults to --rm + tmpfs mounts)

        Returns:
            CompletedProcess result
        """
        run_args = extra_run_args or [
            "--rm",
            "--tmpfs", "/tmp:rw,noexec,nosuid,size=100m,mode=1777",
        ]

        docker_cmd = ["docker", "run"] + run_args

        if attack_dir_abs:
            docker_cmd.extend(["-v", f"{attack_dir_abs}:/attack:ro"])

        docker_cmd.extend([image_name, "sh", "-c"])

        parts = ["mkdir -p /work"]
        parts.append(" ".join(shlex.quote(str(a)) for a in python_args))
        docker_cmd.append(" && ".join(parts))

        logger.info(f"Running Docker container: {' '.join(docker_cmd)}")
        print(f"Running Docker container: {' '.join(docker_cmd)}", file=sys.stderr)
        try:
            result = subprocess.run(docker_cmd, check=True)
            logger.info(f"Container exited successfully")
            return result
        except subprocess.CalledProcessError as e:
            logger.error(f"Container exited with error: {e}")
            raise

    def materialize_environment(
        self,
        task_id: str,
        workdir: Path,
        attack_config: Optional[Dict[str, Any]] = None
    ) -> Path:
        """
        Materialize the task environment.
        
        Note: With the new flow, environment is populated in Docker image during build.
        This method is kept for compatibility but may not be needed.
        
        Args:
            task_id: Task identifier
            workdir: Working directory (not used in new flow)
            attack_config: Optional attack configuration (not used here, applied during build)
            
        Returns:
            Path to work directory (for compatibility)
        """
        # In the new flow, data is already in the Docker image
        # This method is kept for compatibility
        workdir = Path(workdir)
        workdir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Environment will be populated from Docker image (no local materialization needed)")
        return workdir
    
    def get_instruction(self, task_id: str) -> str:
        """
        Get task instruction from instruction.md.
        
        Args:
            task_id: Task identifier
            
        Returns:
            Task instruction text
        """
        instruction_path = self.tasks_root / task_id / "instruction.md"
        
        if not instruction_path.exists():
            raise FileNotFoundError(f"Instruction file not found: {instruction_path}")
        
        return instruction_path.read_text().strip()
    
    def get_environment_files(self, task_id: str) -> List[Path]:
        """
        Get list of files that are in the environment/app/ directory.
        
        Args:
            task_id: Task identifier
            
        Returns:
            List of file paths relative to /app in the container
        """
        app_dir = self.tasks_root / task_id / "environment" / "app"
        
        if not app_dir.exists():
            return []
        
        files = []
        for item in app_dir.rglob("*"):
            if item.is_file():
                # Get relative path from app_dir
                rel_path = item.relative_to(app_dir)
                files.append(rel_path)
        
        return files
    
    def initialize_trace_with_environment(
        self,
        task_id: str,
        trace: 'ExecutionTrace',
        attack_config: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Initialize execution trace with files available in the environment.
        
        This creates initial SurfaceEvents for files that are in the environment,
        so they show up in touched_objects even if the agent doesn't explicitly
        interact with them (or to mark them as available).
        
        Args:
            task_id: Task identifier
            trace: ExecutionTrace to initialize
            attack_config: Optional attack configuration to mark attacked files
        """
        from infuse.tasks.task_suite import SurfaceType, SurfaceEvent
        
        # Get files in environment
        env_files = self.get_environment_files(task_id)
        
        # Load benign overlay to determine surface types for files
        overlay = self.load_benign_overlay(task_id)
        surfaces = overlay.get("surfaces", {})
        
        # Map overlay surface types to actual SurfaceType enum values
        from infuse.surfaces import INJECTION_TO_OBSERVED
        surface_type_mapping = {k.value: v for k, v in INJECTION_TO_OBSERVED.items()}
        
        # Create a mapping of files to their surface types
        file_to_surfaces = {}
        for surface_key, surface_def in surfaces.items():
            if isinstance(surface_def, dict):
                overlay_surface_type = surface_def.get("type")
                # Map to actual SurfaceType enum
                actual_surface_type = surface_type_mapping.get(overlay_surface_type, SurfaceType.FILE_READ)
                file_patterns = surface_def.get("files", [])
                for pattern in file_patterns:
                    # Resolve pattern to actual files
                    for env_file in env_files:
                        if self._matches_pattern(str(env_file), pattern):
                            if env_file not in file_to_surfaces:
                                file_to_surfaces[env_file] = []
                            if actual_surface_type not in file_to_surfaces[env_file]:
                                file_to_surfaces[env_file].append(actual_surface_type)
        
        # Check if this is a FILENAME attack
        is_filename_attack = False
        if attack_config:
            attack = attack_config.get("attack", {})
            attack_surfaces = attack.get("surfaces", {})
            primary_surfaces = attack_surfaces.get("primary", [])
            is_filename_attack = "FILENAME" in primary_surfaces
        
        # Mark attacked files if attack config provided
        attacked_files = set()
        attacked_file_paths = []  # list of /app/<rel> strings for FILENAME and other attacks
        if attack_config:
            # Use the actual attacked files from build process
            # Do NOT use fallback logic with file_patterns - only mark the actually injected files
            if self._last_attacked_files:
                for last_attacked in self._last_attacked_files:
                    attacked_file_str = str(last_attacked)
                    attacked_file_path = f"/app/{attacked_file_str}"

                    if is_filename_attack:
                        # For FILENAME attacks, _last_attacked_files entries are newly created files
                        # They may not be in env_files since they were created during build
                        attacked_file_paths.append(attacked_file_path)
                        logger.info(f"FILENAME attack: using newly created file from build: {attacked_file_str}")
                    else:
                        # For other attacks, find matching env_file
                        for env_file in env_files:
                            if str(env_file) == attacked_file_str or str(Path(env_file).name) == attacked_file_str:
                                attacked_files.add(env_file)
                                break
                        logger.info(f"Using attacked file from build: {attacked_file_str}")
            else:
                # No attacked files from build - injection likely failed
                # Do NOT mark any files as attacked (this was causing the bug where
                # all files matching attack's file_patterns were marked as attacked)
                logger.warning("No attacked files recorded from build - injection may have failed")
        
        # Add initial events for available files
        # Use FILE_READ events so they show up in touched_objects
        for env_file in env_files:
            file_path = f"/app/{env_file}"
            # Get surface types (already mapped to SurfaceType enum values)
            surface_types = file_to_surfaces.get(env_file, [SurfaceType.FILE_READ])
            
            # Use the first surface type (or FILE_READ as default)
            surface_type = surface_types[0] if surface_types else SurfaceType.FILE_READ
            
            # Create a single FILE_READ event per file
            event = SurfaceEvent(
                surface=surface_type,
                content=f"File available in environment: {file_path}",
                path=file_path,
                step=0,  # Step 0 = initialization
                metadata={
                    "object_id": f"file:{file_path}",
                    "initialization": True,
                    "available": True,
                    "attacked": env_file in attacked_files,
                    "all_surfaces": [st.value for st in surface_types],
                    "source": "taint"
                }
            )
            trace.add_event(event)
        
        # Record attacked objects in trace
        if attack_config:
            attack = attack_config.get("attack", {})
            attack_id = str(attack.get("id", "unknown"))
            
            if is_filename_attack and attacked_file_paths:
                # For FILENAME attacks, record each newly created file
                # Use FILE_READ surface type (FILENAME is not a SurfaceType enum value)
                for attacked_file_path in attacked_file_paths:
                    trace.record_attacked_object(
                        object_id=f"file:{attacked_file_path}",
                        surface=SurfaceType.FILE_READ,
                        step=0,  # Attack happens at initialization (step 0)
                        attack_id=attack_id
                    )
                    logger.info(f"Recorded FILENAME attacked object (newly created file): {attacked_file_path} (attack_id={attack_id})")
            elif attacked_files:
                # For other attacks, record attacked files from env_files
                for env_file in attacked_files:
                    file_path = f"/app/{env_file}"
                    surface_types = file_to_surfaces.get(env_file, [SurfaceType.FILE_READ])
                    surface_type = surface_types[0] if surface_types else SurfaceType.FILE_READ
                    
                    # Record attacked object
                    trace.record_attacked_object(
                        object_id=f"file:{file_path}",
                        surface=surface_type,
                        step=0,  # Attack happens at initialization (step 0)
                        attack_id=attack_id
                    )
                    logger.info(f"Recorded attacked object: {file_path} (attack_id={attack_id})")
        
        logger.info(f"Initialized trace with {len(env_files)} files from environment")
    
    def _matches_pattern(self, file_path: str, pattern: str) -> bool:
        """Check if file path matches a pattern (supports glob patterns)."""
        from fnmatch import fnmatch
        
        # Handle simple patterns
        if "*" in pattern:
            return fnmatch(file_path, pattern) or fnmatch(str(Path(file_path).name), pattern)
        else:
            # Exact match
            return file_path == pattern or str(Path(file_path).name) == pattern