"""Console entry point for the Lumi local demo."""

from __future__ import annotations

import argparse

from ..adapters.channel.console import ConsoleChannel
from ..ports.channel import OutboundMessage
from .bootstrap import build_runtime
from .router import HELP


def main() -> None:
    parser = argparse.ArgumentParser(description="Lumi local conversation demo")
    parser.add_argument(
        "--no-ai", action="store_true", help="disable optional Azure OpenAI extraction"
    )
    args = parser.parse_args()
    channel = ConsoleChannel()
    runtime = build_runtime(use_ai=not args.no_ai, identity=channel.identity)
    router, session = runtime.router, runtime.session
    channel.send(OutboundMessage(channel.identity, f"Lumi local. {HELP}"))
    for message in channel.receive():
        try:
            response = router.route(message, session)
        except (ValueError, LookupError) as error:
            response = str(error)
        channel.send(OutboundMessage(message.identity, response))


if __name__ == "__main__":
    main()
