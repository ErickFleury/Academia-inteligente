# Task 25 — Equipment-Aware AI Training Adaptation

**Status:** Implemented — 2026-09-25

## Objective

Connect the implemented Task 21 active equipment catalog to RF-19 AI adaptation
so newly proposed machine-dependent exercise candidates can reference only a
canonical active equipment model that has at least one active physical unit.
This is inventory-existence validation, never real-time availability.

## Requirements covered

- RF-19: integration completion for CA-19.1–CA-19.4 under the approved Task 17
  adaptation flow.
- RF-32/RF-33 and EXT-RF-EQP-01 only as the authoritative equipment-catalog
  boundary consumed by adaptation; this task does not reimplement their CRUD.
- The RF-19 canonical consolidation note that Task 21 constrains
  machine-dependent candidates to active gym-catalog equipment.

## Related rules and constraints

- RN-04/RN-05: authenticated client and instructor authorization/isolation
  remain enforced by the existing adaptation flow.
- RN-12–RN-19 and RN-29–RN-31: AI output remains a proposal, unrelated plan
  content is preserved, instructor review is mandatory, and provider failures
  cannot corrupt the current plan.
- RN-20 applies only to the approved recognized-candidate boundary. This task
  does not create an exercise catalog or exercise CRUD.
- RN-33: equipment deactivation and plan/adaptation history are not
  destructively rewritten.
- DEC-07/DEC-08/DEC-15/DEC-18 preserve the existing client-confirmation,
  structured-output, validation, review, privacy, and history flow.
- EXT-DEC-EQP-01 makes the UUID-identified `EquipmentModel` the canonical
  logical identity, derives active quantity from active `EquipmentUnit` rows,
  and forbids live availability semantics.
- EXT-RF-LANG-01 applies to any new user-visible or accessible copy.

## Prerequisites and dependencies

- Tasks 17 and 21 are implemented.
- Inspect the current adaptation provider schema, proposal persistence,
  instructor review UI, and equipment service before changing contracts.
- Preserve existing provider-neutral AI boundaries and fake adapters; tests
  must not call a live provider.

## Required reading

Read `AGENTS.md`, then this task, then only the following canonical material:

- `docs/requirements.md`: RF-19/CA-19.1–CA-19.4, RF-32/RF-33 only as the
  consumed catalog boundary, RN-04, RN-05, RN-12–RN-20, RN-29–RN-33,
  RNF01, RNF04–RNF06, DEC-07, DEC-08, DEC-15, DEC-18, DEC-19,
  EXT-RF-EQP-01, EXT-RF-LANG-01, and the approved two-level equipment policy;
- `docs/product-extensions.md`: EXT-RF-EQP-01;
- `docs/decisions.md`: EXT-DEC-EQP-01 history only where needed to confirm
  canonical model identity and no-availability language;
- Tasks 17 and 21 plus their current implementation/tests;
- `docs/frontend-design.md` only if the existing instructor review UI needs a
  visible catalog-reference adjustment.

## Exact implementation scope

When generating a structured Task 17 adaptation proposal:

1. query the active equipment catalog through the equipment-domain service;
2. include only active `EquipmentModel` records having at least one active
   `EquipmentUnit` in the minimized provider context;
3. identify each permitted model by canonical UUID plus its display name;
4. require every newly proposed machine-dependent candidate to reference one
   of those UUIDs;
5. revalidate the provider result server-side immediately before persistence;
6. reject a missing, unknown, inactive, or zero-active-unit model reference as
   a controlled invalid-provider response, leaving the current plan and
   proposals unchanged.

A genuinely equipment-free candidate may carry no model reference. A non-empty
machine/equipment requirement without a validated canonical model reference
must not bypass the catalog constraint. The persisted structured adaptation
operation must retain the canonical model relationship needed to survive model
renames while preserving the existing human-readable equipment description for
review/history.

Existing unrelated plan items are not retroactively invalidated when equipment
is later deactivated. Deactivation affects future generated candidates; it does
not rewrite approved plans or retained proposals. Instructor review and final
approval remain unchanged except for presenting the validated model clearly
where the existing UI already shows equipment requirements.

## Backend scope

- Replace the current `equipment_catalog_available: false` extension point with
  a bounded active-model context obtained through the equipment module.
- Extend the provider-neutral structured adaptation contract with a nullable
  canonical equipment-model reference for candidate items.
- Validate references in domain/service logic, not only in prompts or the
  frontend.
- Preserve the existing one-proposal/idempotency/concurrency rules and ensure
  an invalid provider response creates no partial proposal operations.
- Keep the adapter context minimal; do not send unit labels, unit IDs, admin
  audit data, client identifiers, or inactive inventory.

## Persistence and migration scope

Add only the nullable canonical `EquipmentModel` relationship required on
persisted structured adaptation operations, following SQLAlchemy/Alembic and
timestamp conventions. Do not add a mutable quantity, availability flag,
occupancy field, reservation field, telemetry, maintenance, or serial-number
model. Preserve existing rows as valid nullable historical records.

## Frontend scope

- Do not create another equipment catalog or management UI.
- If the instructor adaptation screen requires adjustment, reuse its existing
  Task 08 components and show the canonical model name as inventory context.
- Use “equipamento do catálogo” or “unidade ativa” where clarification is
  needed. Never use “disponível”, “livre”, “disponível agora”, or wording that
  implies current occupancy/use.
- Maintain existing phone, tablet, and desktop behavior for the instructor
  review flow.

## Authorization and privacy

- Keep client-owned AI context and proposal access isolated exactly as in Task
  17.
- The provider receives only active model UUID/name pairs plus the already
  approved minimized adaptation context.
- Do not expose equipment-unit administrative metadata or another client's
  information.

## Integration boundaries

- The equipment module remains the authority for model lifecycle and derived
  active unit count.
- The AI adapter proposes; backend validation decides whether the structured
  reference is acceptable; an instructor still decides approval.
- `active_quantity > 0` means the gym has cataloged active physical units. It
  says nothing about whether a unit is free at the time of training.
- No provider call or proposal changes Task 21 inventory.

## Explicitly out of scope

- Initial-plan generation changes unless strictly required to keep a shared
  provider schema valid; do not expand RF-15 behavior through this task.
- Exercise catalog CRUD, automatic creation of exercises/equipment, or fuzzy
  free-text creation/matching as canonical identity.
- Real-time equipment availability, reservations, occupancy, sensors,
  telemetry, cameras, or machine-use tracking.
- Automatic plan approval/activation, bypassing client confirmation or
  instructor review, or rewriting historical plans after deactivation.
- Payment, billing, plan-purchase, or access-eligibility features.

## Acceptance criteria

- Provider context contains active model UUID/name pairs only for models with
  at least one active unit.
- A machine-dependent candidate referencing an allowed model can enter the
  existing proposal/review flow.
- Unknown, inactive, zero-unit, missing, and mismatched model references fail
  in a controlled way and create no partial proposal or current-plan mutation.
- An equipment-free candidate remains supported without fabricating a catalog
  reference.
- Model rename preserves the persisted canonical relationship; later
  deactivation prevents new generation with that model but does not rewrite
  retained history.
- No API/UI/provider context labels active units as available/free units.
- Existing RF-19 preservation, client decision, instructor review, stale-base,
  idempotency, and provider-failure tests continue to pass.

## Expected tests and validation

Add focused service, adapter-contract, persistence/migration, API, and (only if
changed) frontend tests for active/inactive/zero-unit filtering, canonical UUID
validation, rename/deactivation history, null equipment, atomic rejection,
authorization/privacy, and no-live-availability wording. Use fake providers.

Run the repository-standard targeted backend and frontend commands discovered
from existing configuration, then at minimum:

```bash
git diff --check
git status --short
```

Review the full diff and confirm that no exercise CRUD, inventory mutation,
live availability, camera tracking, payment behavior, or unrelated feature was
introduced.

## Documentation and completion requirements

After implementation, update relevant task/status documentation to record the
Task 17→Task 21 integration and its canonical-ID/no-availability boundary.
Report files changed, tests/results, important decisions, and unresolved issues
as required by `AGENTS.md`.

Stop and ask if a materially new human decision is discovered, including a
need for broader exercise-catalog identity or real-time machine semantics. Do
not commit or push.

## Ready-to-run implementation prompt

Read `AGENTS.md`, then
`docs/tasks/25-equipment-aware-ai-adaptation.md`, then only the requirements,
decisions, and completed task material listed under Required reading. Inspect
the existing adaptation and equipment implementations before editing. Implement
only the active-equipment-catalog constraint for Task 17 AI adaptation. Use
canonical EquipmentModel UUIDs, validate provider output server-side, preserve
instructor review/history, and treat active units only as inventory existence.
Do not add live availability, camera tracking, exercise CRUD, payment behavior,
or automatic approval. Follow `docs/frontend-design.md` if frontend changes are
needed. Stop and ask if another material human decision is required. Run
relevant backend/frontend tests, review the Git diff, and provide the required
completion report. Do not commit or push.
