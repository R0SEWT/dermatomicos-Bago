import ast
from pathlib import Path

from lumi.domain.identity import CaregiverAccount
from lumi.domain.provenance import ExternalIdentity


def test_lumi_does_not_import_acoustic_package():
    root = Path(__file__).parents[2] / "src" / "lumi"
    for path in root.rglob("*.py"):
        tree = ast.parse(path.read_text())
        imported = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.append(node.module)
        assert all(not name.startswith("dermatomicos_bago") for name in imported), path


def test_identity_is_channel_scoped_and_has_no_phone_field():
    identity = ExternalIdentity("whatsapp", "bsuid-opaque")
    assert identity.channel == "whatsapp"
    assert identity.opaque_id == "bsuid-opaque"
    assert "phone" not in CaregiverAccount.__dataclass_fields__


# Heavy speech deps must stay behind the optional [voice] extra: the runtime
# imports them lazily (inside the adapter's __init__), never at module level, so
# `import lumi` on a core-only install never pulls a speech model.
_HEAVY_VOICE_DEPS = {"faster_whisper", "ctranslate2", "torch"}


def test_core_does_not_import_heavy_voice_deps_at_module_level():
    root = Path(__file__).parents[2] / "src" / "lumi"
    for path in root.rglob("*.py"):
        tree = ast.parse(path.read_text())
        module_level = []
        for node in tree.body:  # only direct children -> module-level imports
            if isinstance(node, ast.Import):
                module_level.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                module_level.append(node.module)
        for name in module_level:
            assert name.split(".")[0] not in _HEAVY_VOICE_DEPS, f"{path} -> {name}"
