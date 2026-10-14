"""The assembler must reproduce the legacy payload byte-for-byte, for every attack and variant."""
import pytest

from infuse.injection import AttackSpec, assemble_payload, variant_template
from infuse.injection.assemble import place, poisoned_filename, wrap_as_comment
from infuse.runners.run_single_minisweagent import _build_attack_payload
from tests.conftest import ATTACK_IDS


@pytest.mark.parametrize("attack", ATTACK_IDS)
@pytest.mark.parametrize("variant", ["default", "gcg", "troubleshoot"])
def test_matches_legacy_builder(attack, variant):
    spec = AttackSpec.load(attack, strict=False)
    assert assemble_payload(spec, variant) == _build_attack_payload(spec.raw, variant)


def test_variant_falls_back_to_default_when_missing():
    spec = AttackSpec.load(ATTACK_IDS[0], strict=False)
    spec.id = "999999"
    assert variant_template(spec, "gcg") == spec.payload_template


def test_place_positions():
    assert place("a\nb", "P", "prepend") == "P\na\nb"
    assert place("a\nb", "P", "append") == "a\nb\nP\n"
    assert place("a\nb\n", "P", "append") == "a\nb\nP\n"
    assert place("a\nb\nc\nd\n", "P", "inline") == "a\nb\nP\nc\nd\n"
    assert place("whatever", "P", "replace") == "P"


def test_comment_wrapping(tmp_path):
    assert wrap_as_comment(tmp_path / "x.py", "l1\nl2") == "# l1\n# l2"
    assert wrap_as_comment(tmp_path / "x.js", "l1") == "// l1"
    assert wrap_as_comment(tmp_path / "x.md", "l1") == "l1"


def test_poisoned_filename_is_safe():
    name = poisoned_filename("a/b:c?\n" + "x" * 400)
    assert "/" not in name and ":" not in name and "\n" not in name
    assert name.endswith(".txt") and len(name.encode()) <= 254
