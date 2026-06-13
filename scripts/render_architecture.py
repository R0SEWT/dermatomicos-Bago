"""Render the Lumi architecture as a professional PNG using mingrammer/diagrams.

Pure `diagrams` — imports nothing from ``src/`` so it never drags TensorFlow,
the microphone, or the acoustic experiment into the render. Requires Graphviz
(``dot``) on the system PATH and the ``diagrams`` dev dependency.

Run from anywhere:

    uv run python scripts/render_architecture.py

Output: ``docs/diagrams/lumi_architecture.png``.

The diagram mirrors the real code in ``src/lumi`` (hexagonal core + ports +
adapters) and the production Azure target from ``docs/ARCHITECTURE.md``. Edge
styles encode maturity:

* solid  = implemented today (console / in-memory / markdown / Azure OpenAI)
* dashed = accepted production target, not yet wired (ACS, Azure SQL, Blob)
* dotted grey = cross-cutting identity / secrets
"""

from __future__ import annotations

from pathlib import Path

from diagrams import Cluster, Diagram, Edge
from diagrams.azure.database import SQLDatabases
from diagrams.azure.identity import ActiveDirectory
from diagrams.azure.integration import EventGridTopics
from diagrams.azure.ml import CognitiveServices
from diagrams.azure.security import KeyVaults
from diagrams.azure.storage import BlobStorage
from diagrams.azure.web import AppServices
from diagrams.generic.device import Mobile
from diagrams.programming.language import Python

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "docs" / "diagrams"
OUT_DIR.mkdir(parents=True, exist_ok=True)

GRAPH_ATTR = {
    "fontsize": "22",
    "bgcolor": "white",
    "splines": "spline",
    "pad": "0.6",
    "nodesep": "0.6",
    "ranksep": "1.1",
}
TARGET = {"style": "dashed", "color": "#7a7a7a"}
CROSS = {"style": "dotted", "color": "#9a9a9a"}


def render() -> Path:
    with Diagram(
        "Lumi — Arquitectura de cuidado (WhatsApp)",
        show=False,
        direction="LR",
        filename=str(OUT_DIR / "lumi_architecture"),
        outformat="png",
        graph_attr=GRAPH_ATTR,
    ):
        caregiver = Mobile("Cuidador\n(WhatsApp)")

        with Cluster("Canal de entrada"):
            console = Python("Console adapter\n(dev)")
            acs = EventGridTopics("ACS Advanced Msg\n+ Event Grid")

        with Cluster("Core hexagonal — src/lumi"):
            router = Python("ConversationRouter\napi/router.py")
            app = Python("LumiApplication\napplication/service.py")

            with Cluster("Domain core"):
                domain = Python("Aggregates\nplan · checkin · report · audit")

            with Cluster("Safety (determinista · v1)"):
                safety = Python("policy + ruleset v1\nsafety/")

            with Cluster("Ports (boundary)"):
                ai_port = Python("AIExtractionPort")
                repo_port = Python("RepositoryPort")
                report_port = Python("ReportPort")
                clock_port = Python("Clock / Ids ports")

            router >> app
            app >> Edge(label="política") >> safety
            app >> domain
            app >> ai_port
            app >> repo_port
            app >> report_port
            app >> clock_port

        with Cluster("Adaptadores locales (dev)"):
            repo_local = Python("In-memory repo")
            report_local = Python("Markdown report")
            system_local = Python("SystemClock\n+ UuidGenerator")

        with Cluster("Target de producción — Azure rg-team09"):
            entra = ActiveDirectory("Entra ID /\nManaged Identity")
            aoai = CognitiveServices("Azure OpenAI\ngpt-4.1")
            sql = SQLDatabases("Azure SQL\nDatabase")
            blob = BlobStorage("Blob\nmedia + reportes")
            kv = KeyVaults("Key Vault\nkv-team09")
            compute = AppServices("Compute\n(decisión pendiente)")

        # Inbound: console hoy, ACS como target.
        caregiver >> Edge(label="hoy") >> console >> router
        caregiver >> Edge(label="target", **TARGET) >> acs
        acs >> Edge(**TARGET) >> router

        # AI: el adaptador Azure OpenAI ya está implementado → arista sólida.
        ai_port >> Edge(label="implementado") >> aoai

        # Persistencia / reportes: adaptador local hoy, recurso Azure como target.
        repo_port >> Edge(label="dev") >> repo_local
        repo_port >> Edge(label="target", **TARGET) >> sql
        report_port >> Edge(label="dev") >> report_local
        report_port >> Edge(label="target", **TARGET) >> blob
        clock_port >> system_local

        # Cross-cutting: identidad y secretos.
        entra >> Edge(label="auth", **CROSS) >> aoai
        kv >> Edge(label="secretos", **CROSS) >> compute

    return OUT_DIR / "lumi_architecture.png"


if __name__ == "__main__":
    path = render()
    print(f"wrote {path.relative_to(ROOT)}")
