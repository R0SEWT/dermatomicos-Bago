# Lumi - Target Architecture

## Status

This document defines the accepted target boundaries. Azure Communication Services
Advanced Messaging is the production WhatsApp target and Azure SQL Database is
the production transactional store. Compute, authorization/recovery, clinical
content, and retention still require decisions before production.

## Diagram

![Lumi architecture](diagrams/lumi_architecture.png)

Rendered from `scripts/render_architecture.py` (`uv run python
scripts/render_architecture.py`). Solid edges are implemented today; dashed
edges are the accepted production target; dotted edges are cross-cutting
identity/secrets.

## Design principles

1. Safety invariants live in deterministic code.
2. The language model produces structured proposals, never authoritative state.
3. Medical-plan changes require explicit confirmation and create versions.
4. Every persisted fact retains source, timestamp, actor, and provenance.
5. Channel, model, persistence, media, and report vendors are replaceable.
6. The acoustic experiment cannot be imported by the core application runtime.

## Logical components

### Channel adapters

Normalize inbound text, voice-note metadata, photo metadata, delivery receipts,
and user identity into application commands. Start with a local console/test
harness. The production target is Azure Communication Services Advanced
Messaging with inbound events through Event Grid. Identity is always
`ExternalIdentity(channel, opaque_id)`: ACS adapters must prefer WhatsApp BSUID
fields when `from`/`to` are empty and must never require a phone number.

### Application service

Coordinates one use case at a time: register profiles, propose/confirm a medical
plan, record check-ins, evaluate safety policy, generate reports, and export or
delete caregiver data. It controls transactions and idempotency and contains no
vendor SDK calls.

### Domain core

Planned aggregates and value objects:

- `CaregiverAccount`, `DependentProfile`
- `MedicalPlan`, `MedicalPlanVersion`, `PlanItem`
- `TreatmentMention`, `DailyCheckIn`, `Observation`
- `MediaDocument`, `SafetyDecision`, `CandidatePattern`
- `ClinicianReport`, `AuditEvent`

Required enums:

- `TreatmentSource`: `prescribed`, `non_prescribed`
- `ConfirmationState`: `proposed`, `confirmed`, `rejected`
- `SafetyDisposition`: `continue_recording`, `contact_clinician`, `urgent_care`

Core invariants:

- Only confirmed prescribed items belong to the active medical plan.
- Non-prescribed items cannot schedule adherence reminders.
- Plan edits create a new immutable version.
- Pattern statements cannot contain causal or diagnostic conclusions.
- A report references exact plan and policy versions.

### Safety policy

A deterministic, versioned service evaluates structured observations against a
clinician-owned rule set. Rules and caregiver-facing messages require clinical
approval. The language model can extract candidate observations but cannot
choose the final disposition or suppress a matched rule.

### AI extraction and response composition

Use the unified Azure OpenAI v1 endpoint with the existing `gpt-4.1` deployment
and Microsoft Entra ID authentication. The Python adapter uses `OpenAI` with
`/openai/v1/`; this endpoint does not take an `api_version` parameter. Use
strict Pydantic structured outputs, then validate all output as untrusted input.

Do not use Azure AI Agents Service for this extraction path. Microsoft currently
documents that structured outputs are not supported by Agents Service, and
agentic tool autonomy is unnecessary for this workflow.

### Persistence

The production target is Azure SQL Database. The persistence port must support atomic plan activation,
idempotent inbound events, dependent timelines, audit history, export/deletion,
and record-specific retention.

Local development starts with an in-memory adapter. A production relational
store is preferred because plans, confirmations, reports, and audits are
transaction-sensitive. Azure Storage is for media and report objects, not an
assumed replacement for the transactional system of record.

### Media and reports

- Photos, voice notes, and PDFs use a media-store port.
- Production target: private Azure Blob containers via managed identity.
- Blob names use opaque IDs, never caregiver or child names.
- Signed download links are short-lived and authorization-gated.
- Retention and deletion are explicit and independently testable.

### Observability

Decision required. Logs exclude message bodies, photos, plans, phone numbers,
and prompts by default. Emit correlation IDs, policy versions, latency, token
usage, delivery state, and redacted error categories.

## Request flow

1. Verify and normalize an inbound event.
2. Reject duplicate provider events.
3. Ask the AI extractor for structured candidate observations.
4. Apply schema and domain validation.
5. Evaluate deterministic safety policy.
6. Persist facts, provenance, and policy decision.
7. Compose a response from approved facts and an allowed intent.
8. Send the response and record delivery state.

Medical-plan changes persist as proposals first and activate only after a
separate explicit confirmation command.

## Azure mapping

Existing in `rg-team-09`, `eastus2`:

| Capability | Resource | Planned use |
|---|---|---|
| Model inference | `ais-team09-cg65uw`, deployment `gpt-4.1` | Structured extraction and constrained composition |
| Foundry organization | `aih-team09`, `aip-team09` | Evaluation/project workspace |
| Secret management | `kv-team09-cg65uw` | Future vendor secrets and configuration |
| Object storage | `stteam09cg65uw` | Future private media and generated reports |

Not provisioned: application compute, Azure SQL Database, Azure Communication
Services/WhatsApp onboarding, and application telemetry.

Current security observations:

- Storage requires HTTPS/TLS 1.2 and disallows public blob access.
- Storage network default is `Allow`; production needs a reviewed network design.
- Key Vault uses Azure RBAC but public network access is enabled.
- Production compute should use a dedicated least-privilege managed identity.

## Package layout target

```text
src/lumi/
  domain/
  application/
  safety/
  ports/
  adapters/{ai,channel,persistence,media,reports}/
  api/

src/dermatomicos_bago/  # isolated acoustic research
```

The new `lumi` package must not import from `dermatomicos_bago`. A future
experimental adapter may translate validated research output into a neutral
observation behind a feature flag and separate approval gate.

## Decisions required before production implementation

1. ACS WhatsApp webhook security and WABA onboarding details.
2. Azure SQL migration and disaster-recovery strategy.
3. Compute platform and deployment model.
4. Identity, authorization, and caregiver account recovery.
5. Clinically approved red-flag rules and response copy.
6. Legally reviewed retention, export, deletion, and consent policy.

## Microsoft references validated June 2026

- [Azure OpenAI structured outputs](https://learn.microsoft.com/azure/foundry/openai/how-to/structured-outputs)
- [Unified OpenAI v1 endpoint and Entra authentication](https://learn.microsoft.com/azure/developer/ai/how-to/switching-endpoints)
