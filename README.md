# Lumi

Lumi is a WhatsApp-oriented care copilot for caregivers of babies (6–24 months)
with atopic dermatitis. It helps the caregiver keep an accurate record, follow
the doctor-authored medical plan, observe changes over time, and prepare useful
information for the next consultation.

> The caregiver observes, Lumi understands, the doctor decides.

## Architecture

![Lumi architecture](docs/diagrams/lumi_architecture.png)

Lumi is a hexagonal (ports & adapters) application. The domain core and safety
policy hold the invariants; the language model only produces structured
*proposals* that deterministic code validates before persisting. Every external
concern — channel, AI, persistence, media, reports — sits behind a port so the
local development adapters (console, in-memory, markdown) can be swapped for the
production Azure target (ACS + Event Grid, Azure SQL, Blob, Azure OpenAI) without
touching the core.

Edge legend in the diagram: **solid** = implemented today · **dashed** = accepted
production target, not yet wired · **dotted grey** = cross-cutting identity/secrets.

The diagram is generated, not hand-drawn — regenerate it after architecture
changes with:

```bash
uv run python scripts/render_architecture.py   # → docs/diagrams/lumi_architecture.png
```

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for the full component
breakdown, request flow, and Azure mapping.

## Product boundary

The main product is the longitudinal care workflow described in
[`docs/PRODUCT.md`](docs/PRODUCT.md):

1. Capture and version the doctor-authored medical plan.
2. Record short daily check-ins and label every treatment by source
   (`prescribed` vs `non_prescribed`).
3. Surface descriptive patterns without diagnosing or assigning causality.
4. Generate a concise report for the treating clinician.

Hard rules (enforced in code, not prompts): never diagnose or assign clinical
severity, never add/remove/alter a prescribed treatment, a prescribed item enters
the active plan only after explicit caregiver confirmation (creating an immutable
plan version), and red-flag escalation is a deterministic, clinician-owned policy
the model cannot override.

## Repository map

```text
.
├── docs/
│   ├── PRODUCT.md            Product behavior, language, and non-goals
│   ├── ARCHITECTURE.md       Target boundaries, request flow, Azure mapping
│   ├── RISK_REGISTER.md      Clinical, privacy, AI, and operational risks
│   ├── IMPLEMENTATION_PLAN.md Delivery phases and exit criteria
│   └── diagrams/             Generated architecture PNG
├── src/
│   ├── lumi/                 Main product (must not import the acoustic package)
│   │   ├── domain/           Aggregates & value objects, enums, invariants
│   │   ├── application/      Use-case service, commands, results, AI mapping
│   │   ├── safety/           Deterministic versioned red-flag policy (ruleset v1)
│   │   ├── ports/            Abstract boundaries: ai, channel, repository, …
│   │   ├── adapters/         ai/ (Azure OpenAI), channel/, persistence/, reports/
│   │   └── api/              ConversationRouter + CLI entrypoint (`lumi`)
│   └── dermatomicos_bago/    Isolated acoustic research experiment (not in MVP)
├── scripts/
│   ├── check_azure_environment.py  Verifies Azure resource metadata
│   ├── render_architecture.py      Renders the architecture diagram
│   └── record_dataset.py           Records labeled scratch clips (acoustic)
├── evals/datasets/          Extraction eval data (es-PE)
├── tests/lumi/              Lumi unit tests (domain, application, router, ai)
└── tests/                   Acoustic pipeline tests
```

The `lumi` package must **not** import from `dermatomicos_bago`. TensorFlow,
YAMNet, the microphone, and scratch classification are experimental and are not
runtime dependencies of Lumi.

## Local setup

Prerequisites: Python 3.11, [`uv`](https://docs.astral.sh/uv/), Graphviz (only
for rendering the diagram), and Azure CLI authenticated to the hackathon
subscription.

```bash
cp config.example.json config.json
az account set --subscription b893ca12-45bd-47b3-a0ac-081a74a9d4f6
uv sync                                          # core + dev (incl. diagrams)
uv run python scripts/check_azure_environment.py
uv run ruff check .
uv run pytest -q                                 # add -m "not slow" to skip model/hardware tests
```

For a local Azure OpenAI demo, keep credentials only in the ignored `.env` file
and run:

```bash
uv run --extra azure --env-file .env lumi
```

`AZURE_OPENAI_API_KEY` is supported as a temporary local-demo fallback. Leave it
unset to use Microsoft Entra ID via `DefaultAzureCredential`, which remains the
production authentication target.

`config.json` and `.env` are local-only. Never commit credentials, access keys,
WhatsApp tokens, patient data, photos, audio, or generated clinical reports.

## Current Azure environment

The environment checker expects the existing AI Services account with a
`gpt-4.1` deployment, Foundry project, Storage account, and Key Vault in
`rg-team-09`. Compute, the production database (Azure SQL), the WhatsApp provider
(ACS), and application observability are not provisioned yet; those remain
explicit architecture decisions (see `docs/ARCHITECTURE.md`).

## Acoustic experiment

The acoustic scratch/crying detector under `src/dermatomicos_bago/` is retained
as an experimental module. It is **not** part of the Lumi MVP and must not drive
clinical language, severity decisions, or alerts until it passes a separate
dataset-provenance, consent, performance, privacy, failure-mode, and clinical
validation gate.

## Issue tracking

This project uses **beads** (`bd`) for issue tracking — run `bd ready` to see
available work and `bd prime` for the full workflow. `main` is protected: changes
land through a PR gated on green CI and resolved review conversations.
