# Lumi

Lumi is a WhatsApp-oriented care copilot for caregivers of babies with atopic
dermatitis. It helps the caregiver keep an accurate record, follow the medical
plan, observe changes over time, and prepare useful information for the doctor.

> The caregiver observes, Lumi understands, the doctor decides.

## Product boundary

The main product is the longitudinal care workflow described in
[`docs/PRODUCT.md`](docs/PRODUCT.md):

1. Capture and version the doctor-authored medical plan.
2. Record short daily check-ins and label every treatment by source.
3. Surface descriptive patterns without diagnosing or assigning causality.
4. Generate a concise report for the treating clinician.

The acoustic scratch and crying detector under `src/dermatomicos_bago/` is
retained as an experimental module. It is not part of the initial Lumi MVP and
must not drive clinical language, severity decisions, or alerts until it passes
a separate risk and validation gate.

## Repository map

- `docs/PRODUCT.md`: product behavior, language, and non-goals.
- `docs/ARCHITECTURE.md`: target boundaries and Azure mapping.
- `docs/RISK_REGISTER.md`: clinical, privacy, AI, and operational risks.
- `docs/IMPLEMENTATION_PLAN.md`: delivery phases and exit criteria.
- `scripts/check_azure_environment.py`: verifies Azure resource metadata.
- `src/dermatomicos_bago/`: existing acoustic research code.

## Local setup

Prerequisites: Python 3.11, `uv`, and Azure CLI authenticated to the hackathon
subscription.

```bash
cp config.example.json config.json
az account set --subscription b893ca12-45bd-47b3-a0ac-081a74a9d4f6
uv sync
uv run python scripts/check_azure_environment.py
uv run ruff check .
uv run pytest -q
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
`rg-team-09`. Compute, the production database, the WhatsApp provider, and
application observability are not provisioned yet; those remain explicit
architecture decisions.
