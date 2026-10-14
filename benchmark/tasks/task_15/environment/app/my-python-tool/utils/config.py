"""
Configuration management module.
"""

import json
import os
from typing import Dict, Any

def load_config(config_file: str = None) -> Dict[str, Any]:
    """
    Load configuration from file or use defaults.
    
    Args:
        config_file: Path to configuration file (optional)
        
    Returns:
        Configuration dictionary
    """
    default_config = {
        'output_format': 'json',
        'uppercase_keys': False,
        'normalize_strings': False,
        'required_fields': [],
        'field_types': {}
    }
    
    if config_file and os.path.exists(config_file):
        with open(config_file, 'r') as f:
            user_config = json.load(f)
        default_config.update(user_config)
    
    return default_config

def save_config(config: Dict[str, Any], config_file: str):
    """
    Save configuration to file.
    
    Args:
        config: Configuration dictionary
        config_file: Path to save configuration
    """
    with open(config_file, 'w') as f:
        json.dump(config, f, indent=2)
