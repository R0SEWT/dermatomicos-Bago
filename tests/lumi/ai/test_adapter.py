import logging
from types import SimpleNamespace

from lumi.adapters.ai.azure_openai import AzureOpenAIExtractionAdapter
from lumi.adapters.ai.config import AISettings
from lumi.adapters.ai.schemas import PlanExtractionSchema
from lumi.ports.ai import ExtractionContext


class FakeCompletions:
    def __init__(self, parsed):
        self.parsed = parsed
        self.kwargs = None

    def parse(self, **kwargs):
        self.kwargs = kwargs
        message = SimpleNamespace(refusal=None, parsed=self.parsed)
        return SimpleNamespace(choices=[SimpleNamespace(message=message)])


class FakeClient:
    def __init__(self, parsed):
        self.completions = FakeCompletions(parsed)
        self.beta = SimpleNamespace(
            chat=SimpleNamespace(completions=self.completions)
        )


def test_adapter_uses_structured_parse_and_logs_no_payload(caplog):
    payload = "El pediatra indico crema secreta"
    parsed = PlanExtractionSchema(items=[{
        "description": "crema", "source": "prescribed",
        "verbatim_span": "crema", "confidence": 0.9,
        "ambiguous_source": False, "dose_instructions": None,
        "cadence_hint": None,
    }], warnings=[])
    client = FakeClient(parsed)
    adapter = AzureOpenAIExtractionAdapter(
        AISettings("https://resource.openai.azure.com", "gpt-4.1"), client
    )
    with caplog.at_level(logging.INFO):
        result = adapter.extract_plan_proposal(
            payload, ExtractionContext(correlation_id="corr-1")
        )
    assert result.items[0].description == "crema"
    assert client.completions.kwargs["response_format"] is PlanExtractionSchema
    assert client.completions.kwargs["model"] == "gpt-4.1"
    assert payload not in caplog.text
    assert "corr-1" not in caplog.text


def test_settings_are_v1_and_do_not_read_api_keys(monkeypatch):
    monkeypatch.setenv("AZURE_AI_ENDPOINT", "https://resource.openai.azure.com/")
    monkeypatch.setenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4.1")
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", "must-not-be-read")
    settings = AISettings.from_env()
    assert settings.base_url.endswith("/openai/v1/")
    assert not hasattr(settings, "api_key")
