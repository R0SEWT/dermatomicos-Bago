# Phase 3 evaluation harness (`es-PE-v1`)

Pins the **safety boundary** of AI extraction: the model emits an *untrusted
structured proposal*, and deterministic code (`application/ai_mapping.py` +
`safety/policy.py`) is what upholds the product guardrails. The harness asserts
those guarantees against a curated Peruvian-Spanish golden set.

## What it covers

Golden cases map to the scenarios the implementation plan (Phase 3) calls out:

| Layer | Categories | Invariant asserted |
|-------|-----------|--------------------|
| Plan mapping | `prescribed`, `traditional_remedy`, `ambiguous_source`, `anxiety`, `incomplete` | Ambiguous / source-less items never enter the plan (→ caregiver follow-up); non-prescribed stays non-prescribed (no reminders); nothing is auto-confirmed |
| Red-flag policy | `benign`, `contact`, `urgent`, `boundary` | Disposition is a pure function of typed signals; the model cannot suppress or invent escalation; max-rank rule wins; boundary cases do not over-escalate |
| Language | pattern templates, approved copy | No causal/diagnostic language reaches caregiver-facing text; an injected causal slot is rejected at build |

A coverage test guards against silent shrinkage of the set.

## Running

```bash
# offline (default, CI) — no model, no system libs
uv run pytest tests/lumi/eval -q -m "not live_model"

# live — sends raw es-PE text to the real Azure adapter and asserts each case's
# golden boundary survives whatever the model returns (catches mislabels and
# missed red-flag signals)
LUMI_RUN_LIVE_MODEL=1 uv run --extra azure pytest tests/lumi/eval -m live_model
```

The live test is skipped unless `LUMI_RUN_LIVE_MODEL=1` (the existing live-model
convention; `LUMI_EVAL_LIVE=1` is also accepted) **and** the Azure adapter is
configured (`AZURE_AI_ENDPOINT`/`AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_DEPLOYMENT`).

## Offline vs live

The safety guarantees do not depend on a live model, so the **offline** layer
tests them without one (the golden cases carry the proposal the model would
emit). The **live** layer then asserts each case's *safety-relevant boundary*
holds end-to-end on the real model: the mapped clear sources / follow-up and the
red-flag disposition must match `case.expected`. It pins the boundary, not every
extracted field — a mislabelled ambiguous item or a missed urgent signal fails
the eval, which is exactly the regression an eval gate should catch.

## Versioning

`EVAL_SET_VERSION = "es-PE-v1"` matches `adapters/ai/azure_openai.py`. Bump it
when cases change so report/version stamps stay traceable.

> **Clinical note:** `safety/rulesets/v1.py` (`RULESET_V1`) is a PLACEHOLDER
> pending clinical review (RISK CL-03). This harness validates the *mechanism*,
> never clinical thresholds.
