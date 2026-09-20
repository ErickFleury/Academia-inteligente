# MVP Implementation Plan

## Scope and architecture envelope

The MVP is the 15-item set explicitly listed in requirements section 8.1: RF-01–RF-05, RF-09–RF-13, and RF-15–RF-19. The intended system boundary is a React/TypeScript/Vite client, REST/JSON/OpenAPI backend, PostgreSQL persistence, Docker Compose runtime, and provider-independent adapters for e-mail and AI. Authentication is either Keycloak/OIDC or secure backend-integrated authentication. NestJS/Python responsibilities, concrete topology, libraries, and providers remain unresolved under DEC-03; Task 01 must not choose them silently.

The implementation should be modular around identity/access, clients, onboarding/health, training sheets, conversations, and external integrations. Backend authorization and tenant/client isolation are mandatory. External failures must remain contained by adapters (RNF05/RNF06), and sensitive health and AI context must never cross client boundaries (RN-11, RN-23, RN-29).

## Dependency-ordered batches

1. **Foundation (Task 01):** creates the agreed workspace and quality/runtime baseline after architectural decisions.
2. **Identity and clients (Tasks 02–05):** authentication precedes authorization; both precede protected client operations. Registration/search and lifecycle updates are separated because RF-03 has the unresolved biometric/habilitation dependency.
3. **Invitation and onboarding (Tasks 06–09):** invitation delivery creates the secure entry path; token validation precedes health-data capture; persisted required fields precede completion.
4. **Training and AI (Tasks 10–14):** version lifecycle is established before generation, display, chat, and approved adaptation. This keeps provider calls separate from domain state transitions.
5. **MVP verification (Task 15):** validates the integrated journey and applicable RNFs without taking ownership of new feature behavior.

## Decision gates

| Decision | Classification and affected work |
| --- | --- |
| DEC-01 | Non-blocking: use the explicit section 8.1 MVP until scope is revalidated. |
| DEC-03 | Blocking for Tasks 01, 02, and 06; inherited by later tasks: architecture, auth, e-mail, runtime, and NestJS/Python boundaries. |
| DEC-04 | Blocking for Tasks 02–04, 08, 10, 11, and 14: provisioning, role matrix, health access, and professional identity. |
| DEC-05 | Blocking for Tasks 02 and 05: active versus enabled status and RF-03/biometric interaction. |
| DEC-06 | Blocking for Tasks 06–09: invitation-token policy and approved onboarding schema/editability. |
| DEC-07 | Blocking for Tasks 10, 11, and 14: health severity, review/approval states, and activation. |
| DEC-08 | Blocking for Tasks 11, 13, and 14: AI provider/contract, structured responses, and failure behavior. |
| DEC-15 | Blocking for Tasks 10, 11, and 14 where professional review/manual-edit flows are required by RN-12–RN-19. |
| DEC-16 | Non-blocking for feature work; blocking for formal RNF sign-off in Task 15. |
| DEC-17 | Blocking before migrations in Tasks 04, 08, and 10; resolve only the relevant domain slice. |
| DEC-18 | Blocking for Tasks 08 and 11: health-data access, retention, and safe logging/context handling. |

DEC-02 and DEC-09–DEC-14 concern functionality outside this MVP. They remain unresolved and must not influence MVP implementation unless scope changes.

## Task index

| # | Task | RFs covered | Major RN/RNF | DEC dependencies | Prerequisites | Result |
| --- | --- | --- | --- | --- | --- | --- |
| 01 | Project foundation | Enabler only | RNF04–RNF06 | DEC-03 B; DEC-16/17 NB | None | Agreed runnable/testable project skeleton |
| 02 | Authentication | RF-04 | RN-02, RN-04, RN-23; RNF01, RNF05 | DEC-03/04/05 B | 01 | Active users can authenticate; protected routes reject anonymous access |
| 03 | Authorization | RF-05 | RN-04, RN-05, RN-11; RNF04 | DEC-04 B; DEC-18 NB | 02 | Backend-enforced role/permission boundaries |
| 04 | Client registration and search | RF-01, RF-02 | RN-01, RN-04, RN-05, RN-32; RNF01–RNF04 | DEC-04/17 B; DEC-05 NB | 01–03 | Authorized admins create, list, and search clients |
| 05 | Client profile and status | RF-03 | RN-02, RN-33; RNF04 | DEC-05/17 B | 04 | Client edits and reversible lifecycle state with history preserved |
| 06 | Onboarding invitations | RF-09 | RN-23, RN-32; RNF01, RNF05, RNF06 | DEC-03/06 B | 03, 04 | Recorded e-mail invitation attempts with client-bound links |
| 07 | Secure onboarding access | RF-10 | RN-05, RN-23, RN-32 | DEC-06 B | 06 | Valid, scoped tokens open the correct onboarding |
| 08 | Physical and health onboarding | RF-11, RF-12 | RN-05, RN-11, RN-23; RNF02–RNF04 | DEC-04/06/17/18 B | 03, 07 | Validated, isolated physical and health data capture |
| 09 | Onboarding completion | RF-13 | RN-32; RNF01, RNF04 | DEC-06 B | 08 | Only complete forms transition to completed with timestamp |
| 10 | Training version lifecycle | RF-17 | RN-12, RN-14, RN-16–RN-19, RN-31–RN-33; RNF04 | DEC-04/07/15/17 B | 03, 09 | Persistent immutable versions and one current version |
| 11 | Initial AI training generation | RF-15 | RN-12–RN-19, RN-23, RN-29–RN-31; RNF01, RNF05, RNF06 | DEC-04/07/08/15/18 B | 09, 10 | Safe client-scoped AI proposal creates an initial version through the approved flow |
| 12 | Current training view | RF-16 | RN-05, RN-18; RNF01–RNF03 | Decisions inherited from 10–11 | 10, 11 | Mobile-usable own-current-sheet view and empty state |
| 13 | AI assistant chat | RF-18 | RN-05, RN-16, RN-23, RN-29, RN-30; RNF01, RNF05, RNF06 | DEC-08 B; DEC-07 NB | 11, 12 | Isolated chat using current client context with controlled failures |
| 14 | Dynamic training adaptation | RF-19 | RN-12–RN-18, RN-29–RN-31; RNF04–RNF06 | DEC-04/07/08/15 B | 10, 13 | Approved adaptation creates a new current version without unrelated loss |
| 15 | MVP end-to-end verification | All MVP RFs (verification only) | RN/RNF above; RNF01–RNF06 | DEC-16 B for formal sign-off | 02–14 | Verified critical journey, contracts, isolation, responsiveness, and failure handling |

“B” means blocking; “NB” means non-blocking for that task. Each task file contains the exact CA ownership and implementation boundary.

## Explicitly outside the MVP

RF-06–RF-08, RF-14, and RF-20–RF-33 (including RF-24X/RF-25X) are outside this plan. This excludes password recovery, employee CRUD, post-completion self-review, biometrics/catraca, attendance/occupancy, billing/plans, dashboards, classes, and equipment. Rules that mention unspecified manual training, exercise catalogs, completed-workout history, audit/export, or notification flows constrain the MVP where applicable but do not authorize inventing those flows; DEC-15 must define any required implementation.

## Coverage and ownership check

Every MVP RF appears in an owning task: RF-04 (02), RF-05 (03), RF-01/RF-02 (04), RF-03 (05), RF-09 (06), RF-10 (07), RF-11/RF-12 (08), RF-13 (09), RF-17 (10), RF-15 (11), RF-16 (12), RF-18 (13), and RF-19 (14). Task 15 only re-verifies integration. No out-of-MVP RF is assigned implementation responsibility.
