# Gap Remediation Plan

## 1. Source review

This plan was derived from:

- `docs/requirements-gap-review.md`;
- the current canonical `docs/requirements.md`;
- approved and unresolved decisions in `docs/decisions.md` and
  `docs/product-extensions.md`;
- `docs/implementation-plan.md`, all existing task prompts/reports, and current
  implementation/test evidence inspected only where needed to validate status.

The review's findings were not converted mechanically into tasks. The current
repository revalidation grouped the reported findings into the 30 rows below.
“Blocked” means that no implementation prompt was generated; it does not mean
the original requirement was silently removed.

| # | Gap-review item | Revalidated classification | Basis / disposition |
| --- | --- | --- | --- |
| 1 | RF-03/CA-03.4 biometric readiness | BLOCKED BY UNRESOLVED DEC | Depends on the unselected RF-22 provider and enrollment implementation. |
| 2 | RF-06 account recovery | BLOCKED BY UNRESOLVED DEC | DEC-06 recovery-token issue/expiry/single-use/invalidation policy remains open. CA-06.4 infrastructure already exists. |
| 3 | RF-07/RF-08/RN-03 employee lifecycle | BLOCKED BY UNRESOLVED DEC | DEC-04/DEC-17 leave the employee profile schema, role-assignment matrix, Keycloak provisioning, and lifecycle flow for future definition. |
| 4 | RF-14 own onboarding review | ALREADY IMPLEMENTED | Subject-derived `GET /onboarding/me` returns only the caller's persisted onboarding; the completed form displays values read-only and has no caller-selected client path. |
| 5 | RF-20 facial-result/release portion | BLOCKED BY UNRESOLVED DEC | DEC-11 defines the provider-neutral boundary, but an actual recognition provider and its concrete authenticated result contract are not selected. Task 22 already covers the separate confirmed-passage contract. |
| 6 | RF-21 identity/quality/account-enabled portion | BLOCKED BY UNRESOLVED DEC | Depends on provider selection/calibration and RF-22 subject provisioning. Payment/plan eligibility is separately excluded below. |
| 7 | RF-22/CA-22.1–CA-22.3 biometric enrollment | BLOCKED BY UNRESOLVED DEC | DEC-09 policy is resolved, but CompreFace is only a recommendation; provider/deployment, enrollment API, and technical image-retention capability remain unapproved. |
| 8 | RF-26/RF-27 billing records/views | EXCLUDED — PAYMENT SYSTEM | No billing, charges, invoices, payment status, or financial persistence will be implemented. |
| 9 | RF-28/RF-29 nonfinancial dashboard | NEEDS NEW IMPLEMENTATION TASK | Existing client, attendance, and occupancy modules can satisfy CA-28.1/CA-28.3/CA-29.1 without DEC-13 financial semantics. Assigned to Task 24. |
| 10 | RF-28/RF-29 financial indicators and CA-29.2 | EXCLUDED — PAYMENT SYSTEM | Revenue, profit, monthly/annual billing, and financial placeholders are out of scope. |
| 11 | RF-30/RN-25 class schedule | BLOCKED BY UNRESOLVED DEC | DEC-14 still needs occurrence/recurrence, public/authenticated visibility, capacity, reservation, and exception rules. |
| 12 | RF-31/RN-22/RN-24/RN-35/RN-36 payment/plan validity | EXCLUDED — PAYMENT SYSTEM | Plan purchase, subscription validity, payment confirmation, renewal, delinquency, and payment-based access are out of scope. |
| 13 | RN-08 alternative recognition-failure flow | BLOCKED BY UNRESOLVED DEC | DEC-09 allows one extra attempt and DEC-11 ends the biometric flow without a manual bypass; the required alternative remains undefined. |
| 14 | RN-09 multi-entry block | NO LONGER APPLICABLE | It is conditional on the gym selecting that access rule; no current approved flow selects it. Revisit only through a later access-policy decision. |
| 15 | RN-18 completed-workout preservation | BLOCKED BY UNRESOLVED DEC | DEC-15 leaves the completed-workout domain for future definition; no lifecycle establishes what constitutes completion or its link to plan versions. |
| 16 | RN-20 exercise historical deactivation | BLOCKED BY UNRESOLVED DEC | DEC-15 leaves the exercise-catalog management model for future definition. Task 25 does not create exercise CRUD. |
| 17 | RN-21 evaluation responsibility | BLOCKED BY UNRESOLVED DEC | DEC-15 leaves the evaluation domain, authorized evaluator, schema, and lifecycle undefined. |
| 18 | RN-26 critical notices | BLOCKED BY UNRESOLVED DEC | No approved decision defines recipients, delivery channels, retry/failure behavior, or the exact critical permission/biometric/configuration events. |
| 19 | RN-27 remaining audit ownership | DOCUMENTATION-ONLY | Existing modules implement domain-specific evidence; future tasks must inherit RN-27. A standalone generic audit subsystem is not justified, and approved irreversible client erasure remains an explicit exception. |
| 20 | RN-28 export protection | NO LONGER APPLICABLE | No approved export feature exists. Apply the rule when an export is later approved rather than creating placeholder export infrastructure. |
| 21 | RN-34 biometric exclusion from reports | BLOCKED BY UNRESOLVED DEC | It belongs to future biometric/report work; current APIs have no biometric payload. |
| 22 | RN-37 camera occupancy | DEFERRED — CAMERA TRACKING | DEC-10 keeps cameras future, auxiliary, non-authoritative observations. No current task is generated. |
| 23 | TEC-03 host UFW | MANUAL/EXTERNAL VERIFICATION ONLY | Host network interfaces, deployment access path, and allowed inbound ports are environment-specific and not recorded; Compose already avoids publishing PostgreSQL. Record a host deployment decision before automation. |
| 24 | TEC-10 facial integration tests | BLOCKED BY UNRESOLVED DEC | These tests belong with the provider-selected RF-20–RF-22 implementation. Existing modules already have current-scope automated tests. |
| 25 | Task 19 DEC-16 RNF evidence | MANUAL/EXTERNAL VERIFICATION ONLY | Intended-user, representative viewport/live Keycloak, accessibility, eight-hour soak, and restart-recovery checks require execution/evidence, not new product behavior. |
| 26 | EXT-RF-SOC-01 status uncertainty | ALREADY IMPLEMENTED | Backend, frontend, tests, and commit history implement Task 20. Only planning/canonical status text is stale. |
| 27 | EXT-RF-PRES-01 pending status | ALREADY IMPLEMENTED | Task 23, persistence/API/UI/tests, and commit history are present. |
| 28 | EXT-RF-LANG-01 remaining checks | MANUAL/EXTERNAL VERIFICATION ONLY | Live Keycloak and representative viewport/copy checks remain verification work; current implementation and automated coverage already exist. |
| 29 | Task 21 → RF-19 active-equipment constraint | PARTIALLY IMPLEMENTED — FOLLOW-UP TASK REQUIRED | The catalog is implemented, but adaptation still sends `equipment_catalog_available: false`. Assigned to Task 25. |
| 30 | Stale task/status descriptions | DOCUMENTATION-ONLY | Task 20 and Task 23 are implemented and Task 19 has a report; planning status is synchronized as part of this planning change. |

## 2. New implementation tasks

| Task | Title | Requirement IDs covered | Source gaps | Dependencies | Prompt file |
| --- | --- | --- | --- | --- | --- |
| 24 | Nonfinancial Administrative Dashboard | RF-28 CA-28.1/CA-28.3 and nonfinancial existing-module portion of CA-28.2; RF-29 CA-29.1 | Missing nonfinancial dashboard despite implemented client, attendance, and occupancy sources | Tasks 03, 04, 06, 08, 22 | `docs/tasks/24-nonfinancial-administrative-dashboard.md` |
| 25 | Equipment-Aware AI Training Adaptation | RF-19/Task 17 integration with RF-32/RF-33 and EXT-RF-EQP-01 | Task 17 extension point still does not consume Task 21 | Tasks 17, 21; DEC-07/08/15 and EXT-DEC-EQP-01 | `docs/tasks/25-equipment-aware-ai-adaptation.md` |

Task 24 deliberately closes only the decision-complete nonfinancial dashboard
slice. Task 25 uses canonical EquipmentModel UUIDs and active-unit existence;
it does not interpret inventory as real-time availability.

## 3. Existing tasks that already cover reported gaps

- RF-14 is already covered indirectly by Tasks 10/12 and the current
  `/onboarding/me` API/form: authentication is required, ownership comes from
  the Keycloak subject, completed values are displayed read-only, and no
  cross-client selector exists.
- Task 22 already covers RF-23–RF-25 and the confirmed-passage portion related
  to RF-20; it intentionally does not implement facial recognition or release.
- Task 20 already implements EXT-RF-SOC-01, including the later moderation and
  erasure amendments.
- Task 23 already implements EXT-RF-PRES-01 without changing aggregate
  occupancy.
- Task 19 already supplies the functional integration report and automated
  evidence; its remaining DEC-16 items are manual/external verification, not a
  missing feature task.

## 4. Decision-blocked gaps

| Gap | Requirement | Blocking decision | Exact decision still required |
| --- | --- | --- | --- |
| Recovery | RF-06 CA-06.1–CA-06.3 | DEC-06 | Token issuer, lifetime, hashing/single-use/invalidation, resend behavior, and Keycloak/SMTP handoff. |
| Employee lifecycle | RF-07/RF-08/RN-03 | Future employee slice under DEC-04/DEC-17 | Minimum Employee fields, Account cardinality, role/specialization assignment, who may grant each role, Keycloak provisioning, and deactivation/history behavior. |
| Biometric enrollment and recognition | RF-03 CA-03.4, RF-20–RF-22, RN-10, RN-34, TEC-10 facial portion | DEC-09/DEC-11 implementation selection | Select the recognition provider/runtime and approve its concrete server authentication, enrollment/reference lifecycle, calibrated threshold evidence, callback or synchronous result contract, and deletion capability. |
| Recognition failure alternative | RN-08 | Unresolved relationship between DEC-09 and DEC-11 | Decide what approved non-biometric alternative satisfies RN-08 while preserving the prohibition on an in-flow manual release bypass. |
| Completed workouts | RN-18 | DEC-15 future gate | Define workout completion, its relationship to plan/version/items, correction behavior, and minimum retained history. |
| Exercise lifecycle | RN-20 | DEC-15 future gate | Define the exercise aggregate/identity, management authority, deactivation, and historical-reference behavior. |
| Evaluations | RN-21 | DEC-15 future gate | Define evaluation data, authorized professional, responsibility attribution, edit/correction rules, and retention. |
| Critical notices | RN-26 | New decision required; no current DEC owns it | Define triggering changes, recipients, delivery channel, retry/failure semantics, acknowledgement if any, and relationship to audit records. |
| Class schedule | RF-30/RN-25 | DEC-14 | Define occurrence/recurrence, visibility, capacity, reservations, removal semantics, and authorized exceptions. |

Payment-dependent parts of DEC-12/DEC-13 are not listed as work waiting for a
decision because this plan explicitly excludes payment-system implementation.

## 5. Deferred camera-tracking work

RN-37 and every DEC-10 auxiliary-camera capability remain deferred/future. No
prompt was created for camera person counting, occupancy reconciliation, video
processing, ONVIF, camera-derived presence, or named surveillance. Task 25's
equipment integration and future dedicated turnstile facial recognition do not
alter this exclusion.

## 6. Payment-related exclusions

The following gap-review items are classified **EXCLUDED FROM IMPLEMENTATION —
PAYMENT SYSTEM OUT OF SCOPE**:

- RF-26 and RF-27 billing/financial records and views;
- RF-31 plan purchase/subscription/payment confirmation;
- RN-22, RN-24, RN-35, and RN-36 where they depend on plan validity, renewal,
  delinquency, payment, or payment-based entry eligibility;
- RF-28/CA-28.2 and RF-29/CA-29.2 monthly/annual billing, revenue, profit, or
  other financial dashboard indicators;
- payment gateways, checkout, cards, PIX, boleto, invoices, transaction
  history, and placeholder financial schemas.

Task 24 explicitly contains no financial placeholder and makes no claim for
CA-29.2.

## 7. Manual/external verification remaining

- Complete the outstanding DEC-16 Task 19 evidence: intended-user critical
  journeys, 360×800/768×1024/1366×768 inspection, keyboard/focus/contrast and
  accessibility checks, eight-hour local soak, and five-minute normal-restart
  recovery without data loss.
- Confirm the repository-managed Keycloak theme and EXT-RF-LANG-01 copy in a
  live first-access/login flow and representative viewports.
- Define the actual deployment host/network before documenting or applying UFW
  inbound rules; verify that PostgreSQL and internal services remain
  non-public.

These are evidence or environment activities. They do not justify new product
features.

## 8. Documentation-only work

- Synchronize `docs/implementation-plan.md` with the implemented status of
  Tasks 20 and 23, the partial/manual status of Task 19, and new Tasks 24–25.
- Treat the current progress and presence implementation as evidence despite
  stale status prose in the gap review. Do not rewrite completed historical
  task scopes.
- RN-27 remains an inherited constraint for each future domain, with the
  approved irreversible account-erasure exception documented separately; no
  speculative generic audit service is planned.

No canonical requirement or decision is changed by this planning work.

## 9. Recommended execution order

1. **Task 24 — Nonfinancial Administrative Dashboard.** It uses stable existing
   modules and has no schema dependency on Task 25.
2. **Task 25 — Equipment-Aware AI Training Adaptation.** Run after Task 24 (or
   independently) with focused migration/adapter regression coverage because it
   extends retained adaptation operations.
3. Run the remaining manual/external Task 19 and language checks when the local
   environment and intended user are available.
4. Resolve the blocked decisions before creating biometric, employee,
   recovery, completed-workout, exercise, evaluation, notice, or class
   implementation prompts.

Do not execute either generated implementation prompt as part of this plan.
