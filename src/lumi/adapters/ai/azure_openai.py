"""Azure OpenAI v1 structured extraction.

Microsoft Entra ID is the default. API-key authentication is an explicit local
demo fallback when ``AZURE_OPENAI_API_KEY`` is present.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

from ...ports.ai import (
    AIPlanProposal,
    ExtractionContext,
    ObservationProposal,
    ProposedSafetySignals,
    VersionStamp,
)
from ._sanitize import sanitize_observations, sanitize_plan
from .config import AISettings
from .schemas import (
    OBSERVATION_SCHEMA_VERSION,
    PLAN_SCHEMA_VERSION,
    ObservationExtractionSchema,
    PlanExtractionSchema,
)

_LOG = logging.getLogger(__name__)
_PROMPT_DIR = Path(__file__).with_name("prompts")
PROMPT_VERSION = "v1"
EVAL_SET_VERSION = "es-PE-v1"


class AzureOpenAIExtractionAdapter:
    def __init__(self, settings: AISettings, client: Any | None = None) -> None:
        self._settings = settings
        if client is None:
            from openai import OpenAI

            credential = os.environ.get("AZURE_OPENAI_API_KEY")
            if credential is None:
                from azure.identity import (
                    DefaultAzureCredential,
                    get_bearer_token_provider,
                )

                credential = get_bearer_token_provider(
                    DefaultAzureCredential(),
                    "https://cognitiveservices.azure.com/.default",
                )
            client = OpenAI(
                base_url=settings.base_url,
                api_key=credential,
                timeout=settings.timeout_seconds,
                max_retries=settings.max_retries,
            )
        self._client = client

    def _version(self, schema_version: str) -> VersionStamp:
        return VersionStamp(
            deployment=self._settings.deployment,
            model_version=self._settings.model_version,
            api_version="v1",
            schema_version=schema_version,
            prompt_version=PROMPT_VERSION,
            eval_set_version=EVAL_SET_VERSION,
        )

    @staticmethod
    def _prompt(name: str) -> str:
        return (_PROMPT_DIR / f"{name}.es-PE.{PROMPT_VERSION}.md").read_text()

    @staticmethod
    def _context(context: ExtractionContext) -> str:
        return (
            f"locale={context.locale}; age_months={context.dependent_age_months}; "
            f"active_plan_summary={context.active_plan_summary or 'none'}"
        )

    def extract_plan_proposal(self, text: str, context: ExtractionContext) -> AIPlanProposal:
        version = self._version(PLAN_SCHEMA_VERSION)
        completion = self._client.beta.chat.completions.parse(
            model=self._settings.deployment,
            messages=[
                {"role": "system", "content": self._prompt("plan-extractor")},
                {"role": "developer", "content": self._context(context)},
                {"role": "user", "content": text},
            ],
            response_format=PlanExtractionSchema,
        )
        message = completion.choices[0].message
        _LOG.info(
            "ai_plan_extraction_complete",
            extra={"correlation_id": context.correlation_id, "deployment": version.deployment},
        )
        if message.refusal or message.parsed is None:
            return AIPlanProposal((), version, ("model_refusal",))
        return sanitize_plan(message.parsed, text, version, self._settings.confidence_threshold)

    def extract_daily_observations(
        self, text: str, context: ExtractionContext
    ) -> ObservationProposal:
        version = self._version(OBSERVATION_SCHEMA_VERSION)
        completion = self._client.beta.chat.completions.parse(
            model=self._settings.deployment,
            messages=[
                {"role": "system", "content": self._prompt("observation-extractor")},
                {"role": "developer", "content": self._context(context)},
                {"role": "user", "content": text},
            ],
            response_format=ObservationExtractionSchema,
        )
        message = completion.choices[0].message
        _LOG.info(
            "ai_observation_extraction_complete",
            extra={"correlation_id": context.correlation_id, "deployment": version.deployment},
        )
        if message.refusal or message.parsed is None:
            return ObservationProposal((), ProposedSafetySignals(), version, ("model_refusal",))
        return sanitize_observations(
            message.parsed, text, version, self._settings.confidence_threshold
        )
