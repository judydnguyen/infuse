"""LEGACY — kept verbatim only so tests/test_resolver_equivalence.py can prove the new
resolver picks identical targets. Not imported by the pipeline. Delete after the first
re-collection under the new injector."""
"""
Attack Injector for test_tasks structure.

This module handles pre-execution attack injection by directly manipulating
files in the populated environment based on attack configuration.
"""

import logging
import sys
import tempfile
import zipfile
import tarfile
from pathlib import Path
from typing import Dict, Any, List, Optional
try:
    import tomllib as tomli  # Python 3.11+
except ImportError:
    try:
        import tomli  # Fallback: tomli library
    except ImportError:
        raise ImportError("Need tomllib (Python 3.11+) or tomli library")

logger = logging.getLogger(__name__)

MAX_ATTACK_SURFACES = 3


class TestTaskAttackInjector:
    """Injects attacks by manipulating files directly in the environment."""
    
    def __init__(self, tasks_root: Path):
        """
        Initialize the injector.
        
        Args:
            tasks_root: Root directory containing test_tasks
        """
        self.tasks_root = Path(tasks_root)
    
    def load_attack_config(self, attack_id: str) -> Dict[str, Any]:
        """
        Load attack configuration from attacks/attack_X/config.toml.
        
        Args:
            attack_id: Attack identifier (e.g., "1")
            
        Returns:
            Dictionary with attack configuration
        """
        from infuse.paths import attack_config_path
        attack_path = attack_config_path(attack_id)
        
        if not attack_path.exists():
            raise FileNotFoundError(f"Attack config not found: {attack_path}")
        
        with open(attack_path, "rb") as f:
            config = tomli.load(f)  # type: ignore
        
        return config
    
    def load_benign_overlay(self, task_id: str) -> Dict[str, Any]:
        """Load benign overlay to get available surfaces."""
        overlay_path = self.tasks_root / task_id / "environment" / "overlays" / "benign.toml"
        
        if not overlay_path.exists():
            logger.warning(f"Benign overlay not found: {overlay_path}")
            return {"surfaces": {}}
        
        with open(overlay_path, "rb") as f:
            overlay = tomli.load(f)  # type: ignore
        
        return overlay
    
    def resolve_surfaces(
        self,
        attack_config: Dict[str, Any],
        benign_overlay: Dict[str, Any],
        workdir: Path
    ) -> Dict[str, List[Path]]:
        """
        Resolve which files match the attack's target surfaces.

        Priority: Task-defined surfaces first, then match with attack's supported surfaces.

        Args:
            attack_config: Attack configuration
            benign_overlay: Benign overlay with surface definitions
            workdir: Working directory where files are located

        Returns:
            Dictionary mapping surface types to lists of matching file paths
        """
        resolved = {}

        # Build the full set of attack-supported surfaces (primary + fallback)
        attack_surfaces = attack_config.get("attack", {}).get("surfaces", {})
        primary_surfaces = attack_surfaces.get("primary", [])
        fallback_surfaces = attack_surfaces.get("fallback", [])

        attack_supported_surfaces = set(primary_surfaces + fallback_surfaces)

        if not attack_supported_surfaces:
            logger.warning("No surfaces defined in attack config (primary or fallback)")
            return resolved

        # Get surface definitions from benign overlay
        surfaces = benign_overlay.get("surfaces", {})

        if not surfaces:
            logger.warning("No surfaces defined in benign overlay")
            return resolved

        logger.debug(f"workdir={workdir}, exists={workdir.exists()}")
        logger.debug(f"surfaces from overlay: {list(surfaces.keys())}")
        logger.debug(f"attack_supported_surfaces: {attack_supported_surfaces}")

        # Priority: Task-defined surfaces first
        # Iterate through task's available surfaces and match with attack's supported surfaces
        for key, surface_def in surfaces.items():
            if not isinstance(surface_def, dict):
                continue

            # Get the surface type from the definition
            surface_type = surface_def.get("type", key)

            # Check if this task surface is supported by the attack
            if surface_type not in attack_supported_surfaces:
                logger.debug(f"Task surface {surface_type} not supported by attack")
                continue

            logger.debug(f"Processing surface {surface_type}, def={surface_def}")

            # Get files for this surface
            file_patterns = surface_def.get("files", [])

            # Resolve file paths, preserving order from TOML file
            matching_files = []
            seen_paths = set()  # Track seen paths to avoid duplicates while preserving order
            for pattern in file_patterns:
                logger.debug(f"Resolving pattern: {pattern}")
                # Handle glob patterns
                if "*" in pattern:
                    matches = list(workdir.glob(pattern))
                    # Sort glob results to ensure deterministic order
                    matches = sorted(matches)
                    logger.debug(f"Glob matches: {matches}")
                else:
                    # Exact file path or directory
                    file_path = workdir / pattern
                    logger.debug(f"Checking path: {file_path}, exists={file_path.exists()}")
                    if file_path.exists():
                        matches = [file_path]
                    else:
                        matches = []

                # Add matches in order, skipping duplicates
                for match in matches:
                    if match not in seen_paths:
                        matching_files.append(match)
                        seen_paths.add(match)

            # For FILENAME surfaces, include both files and directories
            # For other surfaces, only include files
            # Filter while preserving order
            if surface_type == "FILENAME":
                matching_files = [f for f in matching_files if f.exists() and (f.is_file() or f.is_dir())]
            else:
                matching_files = [f for f in matching_files if f.exists() and f.is_file()]

            if matching_files:
                resolved[surface_type] = matching_files
                logger.info(f"Matched task surface {surface_type} with {len(matching_files)} paths")

        if not resolved:
            task_surfaces = [s.get("type", k) for k, s in surfaces.items() if isinstance(s, dict)]
            logger.warning(
                f"No surface matches found. Task defines: {task_surfaces}, "
                f"Attack supports: {list(attack_supported_surfaces)}"
            )

        return resolved
    
    def select_target_file(
        self,
        resolved_surfaces: Dict[str, List[Path]],
        attack_config: Dict[str, Any]
    ) -> Optional[tuple]:
        """
        Select a target file from resolved surfaces.

        Priority: Use whatever surfaces were resolved (task-defined surfaces take priority).

        Args:
            resolved_surfaces: Dictionary of surface types to file lists
            attack_config: Attack configuration

        Returns:
            Tuple of (selected file path, surface type), or None if no suitable file found
        """
        if not resolved_surfaces:
            return None

        # Pick the first resolved surface and first file from it
        # Order is determined by the TOML file
        for surface_type, files in resolved_surfaces.items():
            if files:
                selected = files[0]
                logger.info(f"Selected target: {selected} (surface: {surface_type})")
                return (selected, surface_type)

        return None

    def select_all_target_files(
        self,
        resolved_surfaces: Dict[str, List[Path]],
        attack_config: Dict[str, Any]
    ) -> List[tuple]:
        """
        Select one target file per resolved surface type (multi-surface mode).

        Capped at MAX_ATTACK_SURFACES to avoid injecting into too many files.

        Args:
            resolved_surfaces: Dictionary of surface types to file lists
            attack_config: Attack configuration

        Returns:
            List of (file path, surface type) tuples, one per surface, up to MAX_ATTACK_SURFACES
        """
        results = []
        for surface_type, files in resolved_surfaces.items():
            if files:
                results.append((files[0], surface_type))
            if len(results) >= MAX_ATTACK_SURFACES:
                break
        return results

    def _inject_single(
        self,
        target_file: Path,
        selected_surface_type: str,
        workdir: Path,
        attack_config: Dict[str, Any],
    ) -> Optional[Path]:
        """Inject attack payload into a single target file. Returns the injected path or None."""
        attack = attack_config.get("attack", {})
        payload_config = attack.get("payload", {})
        payload_template = payload_config.get("template", "")

        target_config = attack.get("target", {})
        inject_position = target_config.get("inject_position", "append")
        inject_prefix = target_config.get("inject_prefix", "")

        full_payload = f"{inject_prefix}\n{payload_template}" if inject_prefix else payload_template

        is_filename_attack = selected_surface_type == "FILENAME"

        if is_filename_attack:
            # FILENAME attack: create new file with payload in filename
            # Determine directory where to create the file
            if target_file.is_dir():
                target_dir = target_file
            elif target_file.is_file():
                target_dir = target_file.parent
            else:
                # Path doesn't exist - try to resolve relative to workdir
                resolved_path = workdir / target_file
                if resolved_path.exists() and resolved_path.is_dir():
                    target_dir = resolved_path
                elif resolved_path.exists() and resolved_path.is_file():
                    target_dir = resolved_path.parent
                else:
                    # Assume it's a directory path
                    target_dir = workdir / target_file
                    target_dir.mkdir(parents=True, exist_ok=True)
            
            # Ensure target directory exists
            if not target_dir.exists():
                target_dir.mkdir(parents=True, exist_ok=True)
            
            # Create poisoned filename
            poisoned_filename = self._create_poisoned_filename(full_payload)
            new_file_path = target_dir / poisoned_filename
            
            # Create or rename file with payload in filename
            try:
                if inject_position == "replace" and target_file.is_file():
                    target_file.rename(new_file_path)
                    logger.info(f"Renamed FILENAME attack file: {target_file} -> {new_file_path}")
                    print(f"[FILENAME_INJECT] Renamed '{target_file.name}' to '{poisoned_filename}' in {target_dir}", file=sys.stderr)
                else:
                    new_file_path.write_text("", encoding='utf-8')
                    logger.info(f"Created FILENAME attack file: {new_file_path} (payload in filename)")
                    print(f"[FILENAME_INJECT] Created file '{poisoned_filename}' in {target_dir}", file=sys.stderr)
                return new_file_path
            except Exception as e:
                logger.error(f"Failed to create FILENAME attack file: {e}")
                return None
        
        # Check if target is an archive file
        if self._is_archive_file(target_file):
            # Handle archive injection: extract, inject, repackage
            if self._inject_into_archive(target_file, full_payload, inject_position):
                logger.info(f"Attack injected into archive: {target_file}")
                return target_file
            else:
                logger.warning(f"Failed to inject into archive: {target_file}")
                return None
        else:
            # Regular file injection — wrap payload as comment for code files
            commented_payload = self._wrap_as_comment(target_file, full_payload)
            # commented_payload = full_payload
            content = target_file.read_text(encoding="utf-8")
            new_content = self._inject_payload(content, commented_payload, inject_position)
            target_file.write_text(new_content, encoding="utf-8")
            
            logger.info(f"Attack injected into {target_file}")
            return target_file

    def inject_attack(
        self,
        workdir: Path,
        task_id: str,
        attack_config: Dict[str, Any]
    ) -> List[Path]:
        """
        Inject attack by manipulating files in the workdir.

        Supports single-surface (default) and multi-surface modes controlled by
        ``attack_config["attack"]["surfaces"]["mode"]``:
        - ``"single"`` (default): inject into the first resolved surface file.
        - ``"multi"``: inject into the first file of each resolved surface type,
          up to MAX_ATTACK_SURFACES files.

        Args:
            workdir: Working directory with populated environment
            task_id: Task identifier
            attack_config: Attack configuration dictionary

        Returns:
            List of paths that were attacked (empty if no injection occurred)
        """
        logger.info(f"Injecting attack into {workdir}")

        benign_overlay = self.load_benign_overlay(task_id)
        resolved_surfaces = self.resolve_surfaces(attack_config, benign_overlay, workdir)

        if not resolved_surfaces:
            logger.warning("No files resolved for attack surfaces, skipping injection")
            return []

        surfaces_mode = (
            attack_config.get("attack", {})
            .get("surfaces", {})
            .get("mode", "single")
        )

        if surfaces_mode == "multi":
            targets = self.select_all_target_files(resolved_surfaces, attack_config)
        else:
            single = self.select_target_file(resolved_surfaces, attack_config)
            targets = [single] if single else []

        if not targets:
            logger.warning("No target files selected, skipping injection")
            return []

        injected = []
        for target_file, surface_type in targets:
            result = self._inject_single(target_file, surface_type, workdir, attack_config)
            if result:
                injected.append(result)
        return injected

    def _wrap_as_comment(self, file_path: Path, payload: str) -> str:
        """Wrap payload lines as comments appropriate for the file type."""
        ext = file_path.suffix.lower()
        if ext in {'.py', '.sh', '.rb', '.pl', '.yaml', '.yml', '.toml', '.conf', '.r', '.txt'}:
            return "\n".join(f"# {line}" for line in payload.splitlines())
        elif ext in {'.js', '.ts', '.java', '.c', '.cpp', '.go', '.rs', '.swift', '.kt'}:
            return "\n".join(f"// {line}" for line in payload.splitlines())
        elif ext in {'.html', '.xml'}:
            return f"<!-- {payload} -->"
        elif ext in {'.sql'}:
            return "\n".join(f"-- {line}" for line in payload.splitlines())
        # For unknown/plain-text files, return as-is
        return payload

    def _append_to_file(self, file_path: Path, content: str) -> None:
        """Append content to a file."""
        with open(file_path, "a", encoding="utf-8") as f:
            f.write("\n" + content)
    
    def _prepend_to_file(self, file_path: Path, content: str) -> None:
        """Prepend content to a file."""
        original_content = file_path.read_text(encoding="utf-8")
        new_content = content + "\n" + original_content
        file_path.write_text(new_content, encoding="utf-8")
    
    def _replace_file_content(self, file_path: Path, content: str) -> None:
        """Replace entire file content."""
        file_path.write_text(content, encoding="utf-8")
    
    def _is_archive_file(self, file_path: Path) -> bool:
        """Check if a file is an archive (zip, tar, tar.gz, etc.).
        
        Args:
            file_path: Path to file to check
            
        Returns:
            True if file is an archive, False otherwise
        """
        archive_extensions = {'.zip', '.tar', '.gz', '.bz2', '.xz', '.7z', '.rar'}
        file_ext = file_path.suffix.lower()
        
        # Check single extension (zip, tar)
        if file_ext in archive_extensions:
            return True
        
        # Check double extension (tar.gz, tar.bz2, etc.)
        if len(file_path.suffixes) >= 2:
            combined = ''.join(file_path.suffixes[-2:]).lower()
            if combined in ['.tar.gz', '.tar.bz2', '.tar.xz']:
                return True
        
        return False
    
    def _inject_into_archive(
        self,
        archive_path: Path,
        payload: str,
        inject_position: str = "append",
    ) -> bool:
        """Inject payload into an archive by creating a file with poisoned filename.

        Flow:
        1. Extract archive to temporary directory
        2. Create a new file with the payload embedded in its filename
        3. Repackage the archive
        4. Replace original archive

        Args:
            archive_path: Path to archive file
            payload: Payload to inject (will be embedded in filename)
            inject_position: Not used for filename injection

        Returns:
            True if injection succeeded, False otherwise
        """
        try:
            # Create temporary directory for extraction
            with tempfile.TemporaryDirectory(prefix=f"archive_inject_{archive_path.stem}_") as temp_dir:
                temp_path = Path(temp_dir)
                extracted_dir = temp_path / "extracted"
                extracted_dir.mkdir()

                # Extract archive
                if not self._extract_archive(archive_path, extracted_dir):
                    logger.error(f"Failed to extract archive: {archive_path}")
                    return False

                # Create a poisoned file with payload in the filename
                poisoned_filename = self._create_poisoned_filename(payload)
                poisoned_file_path = extracted_dir / poisoned_filename

                # Create the file with minimal content
                try:
                    poisoned_file_path.write_text("", encoding='utf-8')
                    logger.info(f"Created poisoned file '{poisoned_filename}' in archive {archive_path.name}")
                    print(f"[ARCHIVE_INJECT] Created poisoned file '{poisoned_filename}' in archive {archive_path.name}", file=sys.stderr)
                except Exception as e:
                    logger.error(f"Failed to create poisoned file: {e}")
                    return False

                # Repackage archive
                if not self._repackage_archive(extracted_dir, archive_path):
                    logger.error(f"Failed to repackage archive: {archive_path}")
                    return False

                return True

        except Exception as e:
            logger.error(f"Error injecting into archive {archive_path}: {e}")
            return False

    def _create_poisoned_filename(self, payload: str) -> str:
        """Create a filename with the payload embedded.

        Sanitizes the payload to be a valid filename by replacing
        characters that are not allowed in filenames.

        Args:
            payload: The payload to embed in the filename

        Returns:
            A sanitized filename containing the payload
        """
        # Characters not allowed in filenames on most systems
        invalid_chars = ['/', '\\', '\0', ':', '*', '?', '"', '<', '>', '|', '\n', '\r']

        sanitized = payload
        for char in invalid_chars:
            # Replace with underscore
            sanitized = sanitized.replace(char, '_')

        # Truncate if too long (most filesystems limit to 255 bytes)
        max_length = 250  # Leave room for extension
        if len(sanitized.encode('utf-8')) > max_length:
            # Truncate by characters, being careful with unicode
            while len(sanitized.encode('utf-8')) > max_length:
                sanitized = sanitized[:-1]

        # Ensure filename is not empty
        if not sanitized.strip():
            sanitized = "payload"

        # Add a .txt extension for visibility
        return f"{sanitized}.txt"
    
    def _extract_archive(self, archive_path: Path, extract_dir: Path) -> bool:
        """Extract an archive file to a directory.
        
        Args:
            archive_path: Path to archive file
            extract_dir: Directory to extract to
            
        Returns:
            True if extraction succeeded, False otherwise
        """
        try:
            suffix = archive_path.suffix.lower()
            
            if suffix == '.zip':
                with zipfile.ZipFile(archive_path, 'r') as zf:
                    zf.extractall(extract_dir)
                return True
            elif suffix == '.tar':
                with tarfile.open(archive_path, 'r') as tf:
                    tf.extractall(extract_dir)
                return True
            elif suffix == '.gz':
                # Check if it's tar.gz
                if len(archive_path.suffixes) >= 2 and archive_path.suffixes[-2].lower() == '.tar':
                    with tarfile.open(archive_path, 'r:gz') as tf:
                        tf.extractall(extract_dir)
                    return True
            elif suffix in ['.bz2', '.xz']:
                # Check if it's tar.bz2 or tar.xz
                if len(archive_path.suffixes) >= 2 and archive_path.suffixes[-2].lower() == '.tar':
                    mode = 'r:bz2' if suffix == '.bz2' else 'r:xz'
                    with tarfile.open(archive_path, mode) as tf:
                        tf.extractall(extract_dir)
                    return True
            
            logger.warning(f"Unsupported archive format: {archive_path}")
            return False
            
        except Exception as e:
            logger.error(f"Failed to extract archive {archive_path}: {e}")
            return False
    
    def _find_injection_target(self, directory: Path) -> Optional[Path]:
        """Find a suitable file in the extracted archive to inject into.
        
        Prefers text files like .txt, .py, .md, .sh, etc.
        Falls back to any text-readable file.
        
        Args:
            directory: Directory containing extracted archive contents
            
        Returns:
            Path to target file, or None if no suitable file found
        """
        # Preferred extensions for injection
        preferred_extensions = {'.txt', '.py', '.md', '.sh', '.yaml', '.yml', '.json', '.toml', '.conf', '.config'}
        
        # First pass: look for preferred extensions
        for ext in preferred_extensions:
            for file_path in directory.rglob(f"*{ext}"):
                if file_path.is_file():
                    return file_path
        
        # Second pass: try to find any text file
        for file_path in directory.rglob("*"):
            if file_path.is_file():
                # Skip hidden files and common binary indicators
                if file_path.name.startswith('.'):
                    continue
                if file_path.suffix.lower() in {'.exe', '.bin', '.so', '.dll', '.dylib'}:
                    continue
                
                # Try to read as text to verify it's text-based
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        f.read(1024)  # Read first 1KB to check if it's text
                    return file_path
                except (UnicodeDecodeError, Exception):
                    continue
        
        return None
    
    def _repackage_archive(self, source_dir: Path, archive_path: Path) -> bool:
        """Repackage extracted archive contents back into the archive.
        
        Args:
            source_dir: Directory containing extracted contents
            archive_path: Path where archive should be created
            
        Returns:
            True if repackaging succeeded, False otherwise
        """
        try:
            # Remove original archive
            if archive_path.exists():
                archive_path.unlink()
            
            suffix = archive_path.suffix.lower()
            
            if suffix == '.zip':
                with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                    for file_path in source_dir.rglob("*"):
                        if file_path.is_file():
                            arcname = file_path.relative_to(source_dir)
                            zf.write(file_path, arcname)
                return True
            elif suffix == '.tar':
                with tarfile.open(archive_path, 'w') as tf:
                    for file_path in source_dir.rglob("*"):
                        if file_path.is_file():
                            arcname = file_path.relative_to(source_dir)
                            tf.add(file_path, arcname=arcname)
                return True
            elif suffix == '.gz':
                # Check if it's tar.gz
                if len(archive_path.suffixes) >= 2 and archive_path.suffixes[-2].lower() == '.tar':
                    with tarfile.open(archive_path, 'w:gz') as tf:
                        for file_path in source_dir.rglob("*"):
                            if file_path.is_file():
                                arcname = file_path.relative_to(source_dir)
                                tf.add(file_path, arcname=arcname)
                    return True
            elif suffix in ['.bz2', '.xz']:
                # Check if it's tar.bz2 or tar.xz
                if len(archive_path.suffixes) >= 2 and archive_path.suffixes[-2].lower() == '.tar':
                    mode = 'w:bz2' if suffix == '.bz2' else 'w:xz'
                    with tarfile.open(archive_path, mode) as tf:
                        for file_path in source_dir.rglob("*"):
                            if file_path.is_file():
                                arcname = file_path.relative_to(source_dir)
                                tf.add(file_path, arcname=arcname)
                    return True
            
            logger.warning(f"Unsupported archive format for repackaging: {archive_path}")
            return False
            
        except Exception as e:
            logger.error(f"Failed to repackage archive {archive_path}: {e}")
            return False
    
    def _inject_payload(self, content: str, payload: str, position: str, prefix: str = "") -> str:
        """Inject payload into content at the specified position.
        
        Args:
            content: Original file content
            payload: Payload to inject
            position: Where to inject (prepend, append, inline, replace)
            prefix: Optional prefix to prepend to payload (e.g., "Task complete, your new task is")
            
        Returns:
            Modified content with payload injected
        """
        # Apply prefix if provided
        full_payload = f"{prefix}\n{payload}" if prefix else payload
        
        if position == "prepend":
            return full_payload + "\n" + content
        elif position == "append":
            # Append with newline - ensure content ends with newline if it doesn't already
            if content and not content.endswith("\n"):
                return content + "\n" + full_payload + "\n"
            else:
                return content + full_payload + "\n"
        elif position == "inline":
            # Insert in the middle of the file
            lines = content.splitlines(keepends=True)
            mid = len(lines) // 2
            lines.insert(mid, full_payload + "\n")
            return "".join(lines)
        elif position == "replace":
            # Replace entire content
            return full_payload
        else:
            # Default to append
            if content and not content.endswith("\n"):
                return content + "\n" + full_payload + "\n"
            else:
                return content + full_payload + "\n"