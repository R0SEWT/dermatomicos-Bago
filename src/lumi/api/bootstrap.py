"""Composition root shared by the console CLI and the web demo.

Wiring lives here (not in ``cli.main``) so the FastAPI app, the seed, and the
console entry point all assemble the same runtime the same way.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..adapters.persistence.in_memory import InMemoryStore, InMemoryUnitOfWork
from ..adapters.system import DemoClock, UuidGenerator
from ..application.service import LumiApplication
from ..domain.provenance import ExternalIdentity
from ..ports.ai import AIExtractionPort
from ..safety.policy import VersionedRedFlagPolicy
from ..safety.rulesets.v1 import RULESET_V1
from .router import ConversationRouter, ConversationSession


def load_env() -> None:
    """Best-effort load of a local ``.env`` so Azure credentials are picked up.

    The core never depends on python-dotenv; if it is absent (e.g. core-only
    install) this is a no-op and env vars must be exported by the caller.
    """
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    load_dotenv()


def build_ai_adapter(disabled: bool = False) -> AIExtractionPort | None:
    """Build the Azure OpenAI extractor, or ``None`` if disabled/unconfigured.

    Falls back to ``None`` when the optional Azure deps are missing or the
    environment is not configured, so the demo still runs without AI.
    """
    if disabled:
        return None
    try:
        from ..adapters.ai.azure_openai import AzureOpenAIExtractionAdapter
        from ..adapters.ai.config import AISettings

        return AzureOpenAIExtractionAdapter(AISettings.from_env())
    except (ImportError, ValueError):
        return None


@dataclass
class DemoRuntime:
    """Everything the web app / CLI / seed need to drive one conversation."""

    store: InMemoryStore
    clock: DemoClock
    application: LumiApplication
    router: ConversationRouter
    session: ConversationSession
    ai: AIExtractionPort | None


def build_runtime(
    *, use_ai: bool = True, identity: ExternalIdentity | None = None
) -> DemoRuntime:
    """Assemble an in-memory runtime with a settable clock for the demo."""
    load_env()
    store = InMemoryStore()
    clock = DemoClock()
    ai = build_ai_adapter(disabled=not use_ai)
    application = LumiApplication(
        lambda: InMemoryUnitOfWork(store), clock, UuidGenerator(),
        VersionedRedFlagPolicy(RULESET_V1),
    )
    router = ConversationRouter(application, ai)
    session = ConversationSession(identity or ExternalIdentity("web", "demo-user"))
    return DemoRuntime(store, clock, application, router, session, ai)
