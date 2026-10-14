"""Every active module imports without API keys or Docker."""
import importlib
import pkgutil

import pytest

import infuse

SKIP_PREFIXES = ("infuse.agents.minisweagent.run.", "infuse.agents.minisweagent.environments.",
                 "infuse.agents.minisweagent.agents.interactive")  # upstream extras (textual UI, swebench)


def _modules():
    for m in pkgutil.walk_packages(infuse.__path__, prefix="infuse."):
        if m.name.startswith(SKIP_PREFIXES) or m.name.endswith(("._legacy_injector", ".__main__")):
            continue
        yield m.name


@pytest.mark.parametrize("mod", sorted(_modules()))
def test_import(mod):
    importlib.import_module(mod)
