from pathlib import Path
import yaml


def load_job_config(path: str) -> dict:
    content = Path(path).read_text(encoding="utf-8")
    data = yaml.load(content, Loader=yaml.Loader)
    return data
