"""
Environment Factory
Factory function for creating environment instances (local, docker, etc.)
"""

from typing import Any

# Import environment implementations from env module
from infuse.envs.local import LocalEnvironment
from infuse.envs.docker import DockerEnvironment
from infuse.envs.daytona import DaytonaEnvironment


def get_environment(env_config: dict, default_type: str = "local") -> Any:
    """
    Get an environment instance based on configuration.
    
    Args:
        env_config: Environment configuration dictionary
        default_type: Default environment type if not specified in config
        
    Returns:
        Environment instance (LocalEnvironment, DockerEnvironment, etc.)
    """
    # Make a copy to avoid modifying the original
    config = env_config.copy()
    
    # Determine environment type and remove it from config (not a valid kwarg for config classes)
    env_type = config.pop("environment_class", default_type)
    
    if env_type == "docker":
        return DockerEnvironment(**config)
    elif env_type == "local":
        return LocalEnvironment(**config)
    elif env_type == "daytona":
        return DaytonaEnvironment(**config)
    else:
        raise ValueError(
            f"Unknown environment type: {env_type}. Supported: 'local', 'docker', 'daytona'"
        )
