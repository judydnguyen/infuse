"""
Surface Detection
Functions for detecting which surfaces an agent has interacted with based on actions.
"""

import re
from typing import List, Set, Dict, Any, Optional
from infuse.tasks.task_suite import SurfaceType


# Patterns for detecting surface interactions from commands
SURFACE_PATTERNS: Dict[SurfaceType, List[str]] = {
    SurfaceType.FILE_READ: [
        r'\bcat\s+',
        r'\bless\s+',
        r'\bmore\s+',
        r'\bhead\s+',
        r'\btail\s+',
        r'\bgrep\s+.*\s+',
        r'\bawk\s+.*\s+',
        r'\bsed\s+.*\s+',
        r'\bpython\s+.*\.py',
        r'\bpython3\s+.*\.py',
        r'\bnode\s+.*\.js',
        r'\bruby\s+.*\.rb',
        r'\bperl\s+.*\.pl',
        r'<\s+',  # Input redirection (reading)
        r'\bread\s+',
        r'\bopen\s+.*\(',  # Python open() for reading
        r'\bwith\s+open\s*\([^)]*["\']r',  # Python context manager read
        r'\bls\s+(?!-l)',  # List directory contents (reading filenames), but not ls -l (which is metadata)
        r'\bfind\s+',  # Find files (reading directory structure)
    ],
    SurfaceType.FILE_WRITE: [
        r'\becho\s+.*\s*>',
        r'\bprintf\s+.*\s*>',
        r'\bcat\s+.*\s*>>',
        r'\bcat\s+.*\s*>',
        r'\btouch\s+',
        r'\bmkdir\s+',
        r'\brm\s+',
        r'\brmdir\s+',
        r'\bmv\s+',
        r'\bcp\s+',
        r'\bchmod\s+',
        r'\bchown\s+',
        r'\b>',  # Output redirection (writing)
        r'\b>>',  # Append redirection
        r'\bopen\s+.*\([^)]*["\']w',  # Python open() for writing
        r'\bopen\s+.*\([^)]*["\']a',  # Python open() for appending
        r'\bwith\s+open\s*\([^)]*["\']w',  # Python context manager write
        r'\bwith\s+open\s*\([^)]*["\']a',  # Python context manager append
        r'\b\.write\s*\(',
        r'\b\.writelines\s*\(',
    ],
    SurfaceType.CONFIG_READ: [
        r'\bcat\s+.*\.(env|yaml|yml|json|toml|ini|conf|config)',
        r'\bless\s+.*\.(env|yaml|yml|json|toml|ini|conf|config)',
        r'\bgrep\s+.*\.(env|yaml|yml|json|toml|ini|conf|config)',
        r'\b\.env',
        r'\bconfig\.(yaml|yml|json|toml)',
        r'\bsettings\.(yaml|yml|json|toml)',
        r'\b\.gitconfig',
        r'\b\.bashrc',
        r'\b\.zshrc',
        r'\b\.profile',
    ],
    SurfaceType.CONFIG_WRITE: [
        r'\becho\s+.*\s*>.*\.(env|yaml|yml|json|toml|ini|conf|config)',
        r'\b>.*\.(env|yaml|yml|json|toml|ini|conf|config)',
        r'\b>>.*\.(env|yaml|yml|json|toml|ini|conf|config)',
        r'\bsed\s+.*\.(env|yaml|yml|json|toml|ini|conf|config)',
        r'\bchmod\s+.*\.(env|yaml|yml|json|toml|ini|conf|config)',
    ],
    SurfaceType.REPO_READ: [
        r'\bgit\s+show',
        r'\bgit\s+log',
        r'\bgit\s+diff',
        r'\bgit\s+status',
        r'\bgit\s+branch',
        r'\bgit\s+tag',
        r'\bcat\s+.*README',
        r'\bcat\s+.*LICENSE',
        r'\bcat\s+.*CHANGELOG',
        r'\bless\s+.*README',
        r'\bfind\s+.*\.git',
        r'\bls\s+.*\.git',
    ],
    SurfaceType.REPO_WRITE: [
        r'\bgit\s+add',
        r'\bgit\s+commit',
        r'\bgit\s+push',
        r'\bgit\s+rm',
        r'\bgit\s+mv',
        r'\bgit\s+checkout',
        r'\bgit\s+branch\s+-',
        r'\bgit\s+tag\s+-a',
    ],
    SurfaceType.METADATA_READ: [
        r'\bexiftool\s+',
        r'\bexif\s+',
        r'\bfile\s+',
        r'\bstat\s+',
        r'\bls\s+-l',
        r'\bls\s+-la',
        r'\bmd5sum\s+',
        r'\bsha256sum\s+',
        r'\bidentify\s+',  # ImageMagick
    ],
    SurfaceType.LOG_READ: [
        r'\bcat\s+.*\.log',
        r'\btail\s+.*\.log',
        r'\bhead\s+.*\.log',
        r'\bgrep\s+.*\.log',
        r'\bless\s+.*\.log',
        r'\bjournalctl',
        r'\bdmesg',
        r'\btail\s+-f',
        r'\bless\s+/var/log',
    ],
    # TERMINAL_INPUT is not a valid surface type - agents propose actions, they don't interact with terminal input
    # TERMINAL_OUTPUT: Detected from command execution results (handled in execution flow)
    # ERROR_MESSAGE: Detected from stderr/error outputs (handled in execution flow)
    SurfaceType.DOCKER_BUILD: [
        r'\bdocker\s+build',
        r'\bdocker\s+image\s+build',
        r'\bdocker-compose\s+build',
    ],
    SurfaceType.DOCKER_RUN: [
        r'\bdocker\s+run',
        r'\bdocker\s+exec',
        r'\bdocker\s+start',
        r'\bdocker-compose\s+up',
        r'\bdocker-compose\s+run',
    ],
    SurfaceType.NETWORK_ATTEMPT: [
        r'\bcurl\s+',
        r'\bwget\s+',
        r'\bping\s+',
        r'\bnslookup\s+',
        r'\bdig\s+',
        r'\bssh\s+',
        r'\bscp\s+',
        r'\brsync\s+',
        r'\bftp\s+',
        r'\bpython\s+.*requests\.',
        r'\bpython\s+.*urllib\.',
        r'\bpython\s+.*http\.',
        r'\bnode\s+.*http\.',
        r'\bnode\s+.*https\.',
        r'\bnode\s+.*fetch\(',
    ],
    SurfaceType.GENERATED_ARTIFACT_READ: [
        # This is detected by checking if a file was created earlier and is now being read
        # Requires tracking file creation history
    ],
}


def detect_surfaces_from_action(action: str, output: Optional[str] = None) -> Set[SurfaceType]:
    """
    Detect which surfaces an agent has interacted with based on action.
    
    Surface detection provides provenance hints only - it indicates which objects
    were read/written, but doesn't directly trigger injections. In the new model,
    attacks operate on what the agent sees (segments), not what it executes.
    
    Args:
        action: The command/action executed by the agent
        output: Optional output (unused - surface detection is from action only)
        
    Returns:
        Set of SurfaceType enums that were detected (provenance hints)
    """
    detected = set()
    action_lower = action.lower()
    
    # Check each surface type's patterns
    # TERMINAL_OUTPUT is not detected - it's not a surface, just output from commands
    # ERROR_MESSAGE can still be detected for error handling scenarios
    skip_surfaces = {SurfaceType.TERMINAL_OUTPUT}  # Remove TERMINAL_OUTPUT detection
    
    for surface_type, patterns in SURFACE_PATTERNS.items():
        if surface_type in skip_surfaces:
            continue
        for pattern in patterns:
            if re.search(pattern, action_lower, re.IGNORECASE):
                detected.add(surface_type)
                break
    
    # Optionally detect ERROR_MESSAGE from output for error handling
    # (This is kept for backward compatibility, but attacks work on segments now)
    if output:
        error_indicators = [
            r'error',
            r'Error',
            r'ERROR',
            r'failed',
            r'Failed',
            r'exception',
            r'Exception',
            r'traceback',
            r'Traceback',
            r'warning',
            r'Warning',
            r'stderr',
        ]
        for indicator in error_indicators:
            if re.search(indicator, output):
                detected.add(SurfaceType.ERROR_MESSAGE)
                break
    
    return detected


def detect_surfaces_from_actions(actions: List[str], outputs: Optional[List[str]] = None) -> Set[SurfaceType]:
    """
    Detect surfaces from a list of actions.
    
    Args:
        actions: List of actions/commands
        outputs: Optional list of outputs corresponding to each action
        
    Returns:
        Set of all detected SurfaceType enums
    """
    all_detected = set()
    
    if outputs is None:
        outputs = [None] * len(actions)
    
    for action, output in zip(actions, outputs):
        detected = detect_surfaces_from_action(action, output)
        all_detected.update(detected)
    
    return all_detected


def get_object_id(action: str, surface: SurfaceType, path: Optional[str] = None) -> Optional[str]:
    """
    Extract a unique identifier for the object touched by a surface interaction.
    
    This allows tracking individual objects (files, docker images, etc.) so attacks
    can ensure each object is only attacked once.
    
    Args:
        action: The command/action
        surface: The surface type
        path: Optional path from surface event
        
    Returns:
        Unique identifier string for the object, or None if object cannot be identified
    """
    action_lower = action.lower()
    
    if surface == SurfaceType.FILE_READ or surface == SurfaceType.FILE_WRITE:
        # Use path if provided, otherwise extract from action
        if path:
            # Normalize path (resolve relative paths, remove trailing slashes)
            obj_path = path.strip().rstrip('/')
            if obj_path:
                return f"file:{obj_path}"
        
        # Extract file paths from action
        file_patterns = [
            r'\b([/\w\.\-]+\.(py|js|rb|pl|sh|txt|md|json|yaml|yml|xml|html|css|java|cpp|c|h))',
            r'["\']([/\w\.\-]+)["\']',
            r'(?:cat|less|more|head|tail|grep|awk|sed|mv|cp|rm|touch|mkdir|chmod|chown)\s+([/\w\.\-]+)',
        ]
        for pattern in file_patterns:
            matches = re.findall(pattern, action_lower)
            if matches:
                # Extract the actual path (handle tuple results from groups)
                paths = [m[0] if isinstance(m, tuple) else m for m in matches if m]
                if paths:
                    obj_path = paths[0].strip().rstrip('/')
                    return f"file:{obj_path}"
    
    elif surface == SurfaceType.CONFIG_READ or surface == SurfaceType.CONFIG_WRITE:
        if path:
            return f"config:{path.strip().rstrip('/')}"
        # Extract config file paths
        config_matches = re.findall(r'([/\w\.\-]+\.(env|yaml|yml|json|toml|ini|conf|config))', action_lower)
        if config_matches:
            config_path = config_matches[0][0].strip().rstrip('/')
            return f"config:{config_path}"
    
    elif surface == SurfaceType.LOG_READ:
        if path:
            return f"log:{path.strip().rstrip('/')}"
        # Extract log file paths
        log_matches = re.findall(r'([/\w\.\-]+\.log|[\/\w\.\-]+log[\/\w\.\-]*)', action_lower)
        if log_matches:
            log_path = log_matches[0].strip().rstrip('/')
            return f"log:{log_path}"
        # Check for system log commands
        if 'journalctl' in action_lower:
            return "log:systemd"
        if 'dmesg' in action_lower:
            return "log:kernel"
    
    elif surface == SurfaceType.DOCKER_BUILD:
        # Extract docker image name/tag
        image_matches = re.findall(r'-t\s+([\w\.\-\/]+:?[\w\.\-]*)', action_lower)
        if image_matches:
            return f"docker_image:{image_matches[0]}"
        # Check for docker-compose
        if 'docker-compose' in action_lower:
            return "docker_image:compose_project"
    
    elif surface == SurfaceType.DOCKER_RUN:
        # Extract container/image name
        image_matches = re.findall(r'(?:docker|docker-compose)\s+(?:run|exec|start)\s+([\w\.\-\/]+)', action_lower)
        if image_matches:
            return f"docker_container:{image_matches[0]}"
    
    elif surface == SurfaceType.NETWORK_ATTEMPT:
        # Extract URLs/domains
        url_matches = re.findall(r'(https?://[^\s]+|[\w\.\-]+\.[a-z]{2,})', action_lower)
        if url_matches:
            url = url_matches[0]
            # Normalize URL (remove protocol, query params for tracking)
            domain = re.sub(r'https?://', '', url).split('/')[0].split('?')[0]
            return f"network:{domain}"
    
    elif surface == SurfaceType.REPO_READ or surface == SurfaceType.REPO_WRITE:
        if path:
            return f"repo:{path.strip().rstrip('/')}"
        # Check for git commands
        if 'git' in action_lower:
            # Try to extract repo path or use current directory
            return "repo:current"
    
    elif surface == SurfaceType.METADATA_READ:
        if path:
            return f"metadata:{path.strip().rstrip('/')}"
        # Extract file path from metadata commands
        file_matches = re.findall(r'(?:exiftool|exif|file|stat|ls)\s+([/\w\.\-]+)', action_lower)
        if file_matches:
            return f"metadata:{file_matches[0].strip().rstrip('/')}"
    
    elif surface == SurfaceType.TERMINAL_OUTPUT:
        # Terminal output is not a surface - it's just output from commands
        # No object tracking needed
        return None
    
    elif surface == SurfaceType.ERROR_MESSAGE:
        # Error messages don't have a specific object
        return None
    
    # For other surfaces, return None (attack on any instance)
    return None


def get_surface_context(action: str, surface: SurfaceType) -> Dict[str, Any]:
    """
    Extract context information for a specific surface from an action.
    
    Args:
        action: The command/action
        surface: The surface type to extract context for
        
    Returns:
        Dictionary with context information (e.g., file paths, command details)
    """
    context = {
        "action": action,
        "surface": surface.value,
    }
    
    if surface == SurfaceType.FILE_READ or surface == SurfaceType.FILE_WRITE:
        # Extract file paths
        file_patterns = [
            r'\b([/\w\.\-]+\.(py|js|rb|pl|sh|txt|md|json|yaml|yml|xml|html|css|java|cpp|c|h))',
            r'["\']([/\w\.\-]+)["\']',
            r'([/\w\.\-]+)',
        ]
        for pattern in file_patterns:
            matches = re.findall(pattern, action)
            if matches:
                # Extract the actual path (handle tuple results from groups)
                paths = [m[0] if isinstance(m, tuple) else m for m in matches if m]
                if paths:
                    context["paths"] = paths[:5]  # Limit to first 5 paths
                    break
    
    elif surface == SurfaceType.CONFIG_READ or surface == SurfaceType.CONFIG_WRITE:
        # Extract config file paths
        config_matches = re.findall(r'([/\w\.\-]+\.(env|yaml|yml|json|toml|ini|conf|config))', action)
        if config_matches:
            context["config_files"] = [m[0] for m in config_matches]
    
    elif surface == SurfaceType.NETWORK_ATTEMPT:
        # Extract URLs/domains
        url_matches = re.findall(r'(https?://[^\s]+|[\w\.\-]+\.[a-z]{2,})', action)
        if url_matches:
            context["urls"] = url_matches[:5]
    
    return context
