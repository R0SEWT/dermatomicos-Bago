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
