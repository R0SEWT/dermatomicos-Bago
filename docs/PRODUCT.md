# Lumi - Product Map

## Purpose

Lumi is a care copilot for caregivers of babies aged 6-24 months with atopic
dermatitis, initially designed for a WhatsApp conversation in Peru.

The baby cannot describe symptoms. Lumi helps the caregiver preserve an
accurate history, follow the doctor-authored plan, notice repeatable
coincidences, and arrive at the next consultation with useful information.

> The caregiver observes, Lumi understands, the doctor decides.

## Users and ownership

- The caregiver is the account holder and owner of submitted data.
- The baby is a dependent profile, not an independent account.
- The treating clinician receives a report but is not an app user in the MVP.
- Lumi is not a clinician, emergency service, or treatment recommender.

## Movement 0 - Medical plan

The medical plan is created during onboarding and versioned after consultations.
The guided conversation captures preventive care, prescribed medication and its
doctor-authored instructions, bathing/hygiene instructions, the consultation
date, and the next appointment.

Rules:

- Lumi never adds, removes, or changes a prescribed item.
- Editing creates a new plan version; previous versions remain auditable.
- A proposed prescribed item requires explicit caregiver confirmation before it
  becomes active.
- Every treatment mention has one source:
  - `prescribed`: belongs to the confirmed medical plan and may generate
    adherence reminders.
  - `non_prescribed`: home remedy, family advice, social-media recommendation,
    or any item outside the confirmed plan. It is recorded neutrally, never
    generates adherence reminders, and appears in the clinician report.

Example response for an item outside the plan:

> Lo anote. Como no forma parte del plan confirmado por tu pediatra, lo
> incluire en el reporte para que puedan conversarlo en consulta.

## Movement 1 - Daily check-in

One short nightly interaction designed to take less than 30 seconds. Input may
be text, voice note, or photo when the channel adapter supports it.

The record may include food exposures, clothing/fabric/detergent changes,
environmental changes, bathing, plan adherence, sleep, crying, irritability,
observed scratching, products or remedies used, and a dated photo.

Safe language:

- Allowed: observe, record, coincide, repeat, suggest discussing.
- Not allowed: diagnose, detect a flare, determine severity, confirm allergy,
  prove a cause, or declare that waiting is safe.

Red flags are evaluated by a fixed, clinician-reviewed policy. A positive rule
routes the caregiver toward professional care using approved copy. The model
does not create, remove, or override those rules.

## Movement 2 - Longitudinal understanding

### Patterns

Lumi can describe repeated temporal associations using language such as
"coincides with", "repeated after", or "information is missing about". It
cannot state that an exposure caused dermatitis or that the baby has an allergy.
Candidate patterns are marked for clinician validation.

### Visible progress

- Nights without reported scratching.
- Symptom and sleep trends over time.
- Plan adherence over time.
- A chronological photo timeline without image-based diagnosis.

### Magic moment

Target message:

> Las ultimas tres noches con mas molestias ocurrieron uno o dos dias despues
> de [X]. Quieres que lo marque para conversarlo con su pediatra?

The message combines a descriptive pattern, a caregiver action, and the doctor
as final decision-maker.

## Movement 3 - Clinician report

Generate a concise PDF that can be downloaded from the conversation and read in
about 30 seconds. It contains:

- Active medical plan and plan version/date.
- Symptom and sleep evolution.
- Adherence to prescribed items.
- Candidate patterns marked "to validate".
- Other products or remedies marked `non_prescribed`.
- Photos ordered by date.
- Data coverage and missing-data notes.
- Safety disclaimer and generation timestamp.

## Cross-cutting behavior

- Tone is empathetic, direct, and non-judgmental.
- Education is contextual, clinician-approved, and only reinforces the confirmed
  plan; it never reinterprets the plan.
- Proactive check-ins require consent, quiet hours, frequency limits, and opt-out.

## Global guardrails

1. No diagnosis or clinical severity classification.
2. No treatment modification, substitution, or autonomous recommendation.
3. Photos are documentation only.
4. Red flags bias toward professional consultation.
5. Non-prescribed remedies are recorded and reported without judgment.
6. Caregiver ownership, dependent-child privacy, consent, export, and deletion
   are designed into the data model.
7. Every AI-derived field remains attributable to the source message and
   confirmation state.

## MVP

The MVP includes caregiver/dependent profiles, a versioned medical plan,
source-aware treatment records, text check-ins, a deterministic red-flag policy
hook, a longitudinal timeline, factual reports, an audit trail, and a data
deletion path.

The MVP excludes image diagnosis, acoustic monitoring, causal/allergy inference,
autonomous treatment recommendations, a clinician portal, and unreviewed
proactive medical content.
