# Lumi - Implementation Plan

Implementation work is tracked in `bd`. This document defines sequence and exit
criteria so tasks can be created consistently.

## Phase 0 - Foundation

Scope, architecture boundaries, risks, local configuration, Azure validation,
and the experimental boundary are documented and reproducible.

Exit: lint, tests, and `scripts/check_azure_environment.py` pass.

## Phase 1 - Deterministic domain core

Implement `src/lumi/domain`, `application`, `safety`, and `ports` without web,
Azure, WhatsApp, or database dependencies.

First vertical slice:

1. Create caregiver and dependent profile.
2. Propose a medical plan.
3. Confirm and activate a medical-plan version.
4. Record prescribed and non-prescribed treatment mentions.
5. Build a factual report model from stored records.

Exit: plan immutability/versioning tests pass; non-prescribed items cannot create
reminders; records expose actor/source/time/provenance; an in-memory repository
supports all use cases.

## Phase 2 - Conversation API and local adapter

Add a small application API and console/test adapter. Complete Movements 0, 1,
and 3 without a language model. Test idempotency, safety-policy routing, export,
and deletion.

## Phase 3 - Structured AI extraction

Integrate Azure OpenAI v1 with Entra ID and `gpt-4.1`. Use Pydantic structured
outputs for plan proposals and daily observations. Model output cannot mutate
persistence. Ambiguous sources require caregiver confirmation. Gate changes on
an evaluation set for Peruvian Spanish, traditional remedies, anxiety, and
incomplete messages.

## Phase 4 - Persistence, media, and reports

After architecture decisions are accepted, add the transactional repository,
migrations, private Blob storage, retention/deletion, and factual PDF rendering.

Exit: plan activation is atomic, reports are reproducible, deletion covers all
stores, and health data does not appear in logs.

## Phase 5 - WhatsApp and proactive workflows

After selecting a provider, implement webhook verification, normalized events,
durable retries, idempotency, consented reminders, quiet hours, and opt-out.

Exit: duplicate/out-of-order events and provider outage recovery pass; reminders
cannot include non-prescribed treatments; the demo reaches the magic moment and
clinician report.

## Phase 6 - Production hardening

Managed identity, least-privilege RBAC, privacy-safe telemetry, threat model,
backup/restore, incident response, cost controls, and clinical/legal review.

## Deferred experiment

Evaluate the acoustic module only after the main product passes its exit gates.
It receives a separate data, privacy, performance, and clinical validation plan
and remains disabled by default.
