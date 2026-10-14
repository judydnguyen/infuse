import os
import sys
from pathlib import Path

os.environ.setdefault("MSWEA_SILENT_STARTUP", "1")
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pytest  # noqa: E402

from infuse import paths  # noqa: E402


def _ids(prefix: str, root: Path) -> list[str]:
    return sorted((p.name for p in root.iterdir() if p.name.startswith(prefix)),
                  key=lambda n: int(n.split("_")[1]))


ATTACK_IDS = _ids("attack_", paths.ATTACKS_DIR)
TASK_IDS = _ids("task_", paths.TASKS_DIR)


@pytest.fixture(scope="session")
def attack_ids():
    return ATTACK_IDS


@pytest.fixture(scope="session")
def task_ids():
    return TASK_IDS
