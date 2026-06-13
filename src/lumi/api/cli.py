"""Console entry point for the Lumi local demo."""

from __future__ import annotations

import argparse

from ..adapters.channel.console import ConsoleChannel
from ..adapters.persistence.in_memory import InMemoryStore, InMemoryUnitOfWork
from ..adapters.system import SystemClock, UuidGenerator
from ..application.service import LumiApplication
from ..ports.channel import OutboundMessage
from ..safety.policy import VersionedRedFlagPolicy
from ..safety.rulesets.v1 import RULESET_V1
from .router import ConversationRouter, ConversationSession, HELP


def _ai_adapter(disabled: bool):
    if disabled:
        return None
    try:
        from ..adapters.ai.azure_openai import AzureOpenAIExtractionAdapter
        from ..adapters.ai.config import AISettings

        return AzureOpenAIExtractionAdapter(AISettings.from_env())
    except (ImportError, ValueError):
        return None


def main() -> None:
    parser = argparse.ArgumentParser(description="Lumi local conversation demo")
    parser.add_argument(
        "--no-ai", action="store_true", help="disable optional Azure OpenAI extraction"
    )
    args = parser.parse_args()
    store = InMemoryStore()
    application = LumiApplication(
        lambda: InMemoryUnitOfWork(store), SystemClock(), UuidGenerator(),
        VersionedRedFlagPolicy(RULESET_V1),
    )
    channel = ConsoleChannel()
    router = ConversationRouter(application, _ai_adapter(args.no_ai))
    session = ConversationSession(channel.identity)
    channel.send(OutboundMessage(channel.identity, f"Lumi local. {HELP}"))
    for message in channel.receive():
        try:
            response = router.route(message, session)
        except (ValueError, LookupError) as error:
            response = str(error)
        channel.send(OutboundMessage(message.identity, response))


if __name__ == "__main__":
    main()
