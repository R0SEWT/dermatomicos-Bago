# Lumi - Risk Register

This is an engineering risk register, not clinical or legal approval. Clinical
content requires specialist review. Privacy and regulatory requirements require
review by qualified counsel and the data controller.

| ID | Risk | Required control | Release gate |
|---|---|---|---|
| CL-01 | Lumi changes or invents treatment instructions | Immutable confirmed plan, deterministic authorization, no free-form plan writes | Adversarial tests prove model output cannot activate or edit a plan |
| CL-02 | A non-prescribed remedy is treated as prescribed | Source enum, explicit confirmation, no automatic source promotion | Domain tests cover ambiguous and conflicting mentions |
| CL-03 | False reassurance delays care | Clinician-owned red-flag policy biased toward consultation | Clinical owner approves rules, copy, and test cases |
| CL-04 | Excess escalation creates alert fatigue | Versioned rules and measured false-positive review | Pilot defines acceptable escalation behavior |
| CL-05 | Pattern language implies causality or allergy | Restricted templates and causal-language validation | Tests reject diagnostic and causal claims |
| CL-06 | A photo is interpreted as diagnosis or severity | Documentation only; no vision inference in MVP | No production code sends photos to a model |
| AI-01 | Prompt injection changes policy or accesses another case | Model has no persistence tools; isolate case context; validate output | Cross-case and injection tests pass |
| AI-02 | Extraction omits critical information | Preserve source message and ambiguity; deterministic follow-up | Evaluation set includes omissions and ambiguous Spanish |
| AI-03 | Model or prompt drift changes behavior | Pin deployment/schema/prompt/evaluation versions | Offline evaluation gates promotion |
| PR-01 | Child health data appears in logs | Redaction by default; prohibit payload and prompt logging | Log inspection finds no identifiers or health content |
| PR-02 | Media or reports outlive consent | Record-specific retention and verified deletion | End-to-end deletion covers records and blobs |
| PR-03 | Caregiver cannot export or correct records | Export, correction, version history, and audit | Product and legal owners approve workflow |
| PR-04 | A shared phone exposes child records | Account recovery and re-verification design | Identity decision and threat model accepted |
| SEC-01 | Secrets enter Git or app configuration | Managed identity, Key Vault, ignored local config, secret scanning | CI and repository scan pass |
| SEC-02 | Public endpoints expose data | Least privilege, private containers, HTTPS, network review | Infrastructure review passes |
| OP-01 | Duplicate channel events duplicate records | Provider event ID idempotency | Integration test replays duplicate events |
| OP-02 | Provider outage loses submissions | Durable inbound queue/retry and delivery state | Failure-injection test demonstrates recovery |
| OP-03 | Reports cannot be audited | Reference source records, plan/policy versions, timestamp | Reproducibility test passes |
| EX-01 | Acoustic output is presented as validated severity | Separate package, feature flag, neutral terminology | Product works with experiment disabled |
| EX-02 | Audio captures household conversations | No audio collection in MVP | Separate privacy, clinical, and architecture approval |

## Acoustic experiment gate

The acoustic module can only enter a user-facing pilot after:

1. Dataset provenance and consent are documented.
2. Performance is measured on representative independent data.
3. Failure modes and subgroup limitations are documented.
4. Raw-audio retention and bystander privacy are approved.
5. Clinical reviewers approve the intended interpretation.
6. User-facing language avoids diagnosis, severity, and prediction claims.
7. The product remains functional when the experiment is disabled.
