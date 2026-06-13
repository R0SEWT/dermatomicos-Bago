"""Environment-backed, keyless Azure OpenAI settings."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class AISettings:
    endpoint: str
    deployment: str
    model_version: str = "2025-04-14"
    confidence_threshold: float = 0.65
    timeout_seconds: float = 30.0
    max_retries: int = 2

    @classmethod
    def from_env(cls) -> "AISettings":
        endpoint = os.environ.get("AZURE_AI_ENDPOINT") or os.environ.get(
            "AZURE_OPENAI_ENDPOINT"
        )
        deployment = os.environ.get("AZURE_OPENAI_DEPLOYMENT")
        if not endpoint or not deployment:
            raise ValueError(
                "AZURE_AI_ENDPOINT (or AZURE_OPENAI_ENDPOINT) and "
                "AZURE_OPENAI_DEPLOYMENT are required"
            )
        return cls(
            endpoint=endpoint,
            deployment=deployment,
            model_version=os.environ.get("AZURE_OPENAI_MODEL_VERSION", "2025-04-14"),
            confidence_threshold=float(os.environ.get("LUMI_AI_CONFIDENCE_THRESHOLD", "0.65")),
            timeout_seconds=float(os.environ.get("LUMI_AI_TIMEOUT_SECONDS", "30")),
            max_retries=int(os.environ.get("LUMI_AI_MAX_RETRIES", "2")),
        )

    @property
    def base_url(self) -> str:
        endpoint = self.endpoint.rstrip("/")
        if endpoint.endswith("/openai/v1"):
            return f"{endpoint}/"
        return f"{endpoint}/openai/v1/"
