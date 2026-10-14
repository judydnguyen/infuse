"""Config loader module."""
import yaml
import os


def load_config(path):
    # BUG: does not handle missing file
    with open(path, "r") as f:
        return yaml.safe_load(f)


def get_config_value(config, key):
    # BUG: does not handle missing key
    return config[key]


def get_nested_value(config, *keys):
    result = config
    for key in keys:
        result = result[key]
    return result


def merge_configs(base, override):
    merged = base.copy()
    merged.update(override)
    return merged


if __name__ == "__main__":
    config = load_config("config.yaml")
    print(get_config_value(config, "app_name"))
