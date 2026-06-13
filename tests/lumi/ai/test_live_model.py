import os

import pytest

from lumi.adapters.ai.azure_openai import AzureOpenAIExtractionAdapter
from lumi.adapters.ai.config import AISettings
from lumi.ports.ai import ExtractionContext

pytestmark = pytest.mark.live_model


@pytest.mark.skipif(
    os.environ.get("LUMI_RUN_LIVE_MODEL") != "1",
    reason="set LUMI_RUN_LIVE_MODEL=1 with Azure credentials to run",
)
def test_live_plan_extraction_is_grounded():
    adapter = AzureOpenAIExtractionAdapter(AISettings.from_env())
    result = adapter.extract_plan_proposal(
        "El pediatra indico aplicar la crema dos veces al dia.",
        ExtractionContext(correlation_id="live-eval-plan"),
    )
    assert result.items
    assert all(item.verbatim_span for item in result.items)
    assert all(not item.ambiguous_source for item in result.items)
