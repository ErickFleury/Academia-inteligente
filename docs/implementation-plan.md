# MVP Implementation Plan

## Scope and architecture envelope

The MVP is the 15-item set explicitly listed in requirements section 8.1: RF-01–RF-05, RF-09–RF-13, and RF-15–RF-19. The approved system boundary is a React/TypeScript/Vite client, FastAPI modular-monolith backend, PostgreSQL persistence, Keycloak/OIDC identity, Docker Compose runtime, and provider-independent adapters for e-mail and AI, as recorded in DEC-03. The new Task 06 must use that established topology and must not introduce a second authentication store or backend technology.

The implementation should be modular around identity/access, clients, onboarding/health, training sheets, conversations, and external integrations. Backend authorization and tenant/client isolation are mandatory. External failures must remain contained by adapters (RNF05/RNF06), and sensitive health and AI context must never cross client boundaries (RN-11, RN-23, RN-29).

## Dependency-ordered batches

1. **Foundation (Task 01):** creates the agreed workspace and quality/runtime baseline after architectural decisions.
2. **Identity and clients (Tasks 02–06):** authentication precedes authorization; both precede protected client operations. Tasks 04–05 retain ownership of the already-completed local client/account behavior; Task 06 adds the subsequently approved Keycloak provisioning and first-access integration.
3. **Invitation and onboarding (Tasks 07–10):** identity provisioning precedes the client journey; invitation delivery creates the secure onboarding entry path, token validation precedes health-data capture, and persisted required fields precede completion.
4. **Training and AI (Tasks 11–15):** version lifecycle is established before generation, display, chat, and approved adaptation. This keeps provider calls separate from domain state transitions.
5. **MVP verification (Task 16):** validates the integrated journey and applicable RNFs without taking ownership of new feature behavior.

## Decision gates

| Decision | Classification and affected work |
| --- | --- |
| DEC-01 | Non-blocking: use the explicit section 8.1 MVP until scope is revalidated. |
| DEC-03 | Blocking for Tasks 01, 02, and 06; inherited by later tasks: architecture, auth, e-mail, runtime, and NestJS/Python boundaries. |
| DEC-04 | Blocking for Tasks 02–04, 06, 09, 11, 12, and 15: provisioning, role matrix, health access, and professional identity. |
| DEC-05 | Blocking for Tasks 02, 05, and 06: active versus enabled status, RF-03/biometric interaction, and provisioned-client login eligibility. |
| DEC-06 | Blocking for Tasks 07–10: invitation-token policy and approved onboarding schema/editability. |
| DEC-07 | Blocking for Tasks 11, 12, and 15: health severity, review/approval states, and activation. |
| DEC-08 | Blocking for Tasks 12, 14, and 15: AI provider/contract, structured responses, and failure behavior. |
| DEC-15 | Blocking for Tasks 11, 12, and 15 where professional review/manual-edit flows are required by RN-12–RN-19. |
| DEC-16 | Non-blocking for feature work; blocking for formal RNF sign-off in Task 16. |
| DEC-17 | Blocking before migrations in Tasks 04, 06, 09, and 11; resolve only the relevant domain slice. |
| DEC-18 | Blocking for Tasks 09 and 12: health-data access, retention, and safe logging/context handling. |

DEC-02 and DEC-09–DEC-14 concern functionality outside this MVP. They remain unresolved and must not influence MVP implementation unless scope changes.

## Task index

| # | Task | RFs covered | Major RN/RNF | DEC dependencies | Prerequisites | Result |
| --- | --- | --- | --- | --- | --- | --- |
| 01 | Project foundation | Enabler only | RNF04–RNF06 | DEC-03 B; DEC-16/17 NB | None | Agreed runnable/testable project skeleton |
| 02 | Authentication | RF-04 | RN-02, RN-04, RN-23; RNF01, RNF05 | DEC-03/04/05 B | 01 | Active users can authenticate; protected routes reject anonymous access |
| 03 | Authorization | RF-05 | RN-04, RN-05, RN-11; RNF04 | DEC-04 B; DEC-18 NB | 02 | Backend-enforced role/permission boundaries |
| 04 | Client registration and search | RF-01, RF-02 | RN-01, RN-04, RN-05, RN-32; RNF01–RNF04 | DEC-04/17 B; DEC-05 NB | 01–03 | Authorized admins create, list, and search clients |
| 05 | Client profile and status | RF-03 | RN-02, RN-33; RNF04 | DEC-05/17 B | 04 | Client edits and reversible lifecycle state with history preserved |
| 06 | Client identity provisioning | RF-01, RF-04, RF-05 (integration) | RN-01, RN-02, RN-04, RN-05, RN-23, RN-32; RNF01, RNF04–RNF06 | DEC-03/04/05/17 B | 02–05 | Admin-created clients receive a client-only Keycloak identity, persisted subject linkage, and secure first access |
| 07 | Onboarding invitations | RF-09 | RN-23, RN-32; RNF01, RNF05, RNF06 | DEC-03/06 B | 03, 04, 06 | Recorded e-mail invitation attempts with client-bound links |
| 08 | Secure onboarding access | RF-10 | RN-05, RN-23, RN-32 | DEC-06 B | 07 | Valid, scoped tokens open the correct onboarding |
| 09 | Physical and health onboarding | RF-11, RF-12 | RN-05, RN-11, RN-23; RNF02–RNF04 | DEC-04/06/17/18 B | 03, 08 | Validated, isolated physical and health data capture |
| 10 | Onboarding completion | RF-13 | RN-32; RNF01, RNF04 | DEC-06 B | 09 | Only complete forms transition to completed with timestamp |
| 11 | Training version lifecycle | RF-17 | RN-12, RN-14, RN-16–RN-19, RN-31–RN-33; RNF04 | DEC-04/07/15/17 B | 03, 10 | Persistent immutable versions and one current version |
| 12 | Initial AI training generation | RF-15 | RN-12–RN-19, RN-23, RN-29–RN-31; RNF01, RNF05, RNF06 | DEC-04/07/08/15/18 B | 10, 11 | Safe client-scoped AI proposal creates an initial version through the approved flow |
| 13 | Current training view | RF-16 | RN-05, RN-18; RNF01–RNF03 | Decisions inherited from 06, 11–12 | 06, 11, 12 | Mobile-usable own-current-sheet view and empty state for a provisioned authenticated client |
| 14 | AI assistant chat | RF-18 | RN-05, RN-16, RN-23, RN-29, RN-30; RNF01, RNF05, RNF06 | DEC-08 B; DEC-07 NB | 06, 12, 13 | Isolated authenticated-client chat using current context with controlled failures |
| 15 | Dynamic training adaptation | RF-19 | RN-12–RN-18, RN-29–RN-31; RNF04–RNF06 | DEC-04/07/08/15 B | 11, 14 | Approved adaptation creates a new current version without unrelated loss |
| 16 | MVP end-to-end verification | All MVP RFs (verification only) | RN/RNF above; RNF01–RNF06 | DEC-16 B for formal sign-off | 02–15 | Verified critical journey, including identity provisioning/first access, contracts, isolation, responsiveness, and failure handling |

“B” means blocking; “NB” means non-blocking for that task. Each task file contains the exact CA ownership and implementation boundary.

## Effect on completed tasks

Tasks 02–05 remain completed according to their original scopes and are not
retroactively credited with the new behavior. The approved flow exposes these
integration gaps:

- Task 02 established OIDC authentication but did not create client identities
  or their first-access credentials.
- Task 03 established reusable authorization but must be re-verified with a
  genuinely provisioned `client` role and direct administrative API attempts.
- Task 04 created the local account/client atomically with a nullable
  `keycloak_subject`; it did not provision Keycloak.
- Task 05 made `account_active` authoritative for application login and remains
  separate from physical access; Task 06 must verify that behavior for a
  provisioned client.

Task 06 owns only this missing cross-system integration and its compensation
behavior. It integration-verifies RF-01, RF-04, and RF-05 without transferring
their original CA ownership from Tasks 02–04.

## Explicitly outside the MVP

RF-06–RF-08, RF-14, and RF-20–RF-33 (including RF-24X/RF-25X) are outside this plan. This excludes password recovery, employee CRUD, post-completion self-review, biometrics/catraca, attendance/occupancy, billing/plans, dashboards, classes, and equipment. Rules that mention unspecified manual training, exercise catalogs, completed-workout history, audit/export, or notification flows constrain the MVP where applicable but do not authorize inventing those flows; DEC-15 must define any required implementation.

## Coverage and ownership check

Every MVP RF appears in an owning task: RF-04 (02), RF-05 (03), RF-01/RF-02 (04), RF-03 (05), RF-09 (07), RF-10 (08), RF-11/RF-12 (09), RF-13 (10), RF-17 (11), RF-15 (12), RF-16 (13), RF-18 (14), and RF-19 (15). Task 06 integrates RF-01/RF-04/RF-05 without changing ownership; Task 16 only re-verifies integration. No out-of-MVP RF is assigned implementation responsibility.
