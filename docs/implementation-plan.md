# Academia Inteligente Implementation Plan

## Specification and architecture envelope

`docs/requirements.md` is the sole canonical implementation specification. It
contains the 33 RFs and their CA, 6 RNFs, 37 RN, 10 TEC entries, MVP scope,
DEC status, and approved extensions. `docs/decisions.md` and
`docs/product-extensions.md` retain supporting history; `docs/frontend-design.md`
defines shared visual conventions. A conflict with the canonical specification
stops the affected task until a human resolves it.

The original MVP remains RF-01–RF-05, RF-09–RF-13, and RF-15–RF-19. DEC-19
adds EXT-RF-AI-01 conversational onboarding to the planned MVP experience; it
does not rewrite the historical MVP. EXT-RF-SOC-01, EXT-RF-SOC-02,
EXT-RF-EQP-01, and EXT-RF-PRES-01 are approved post-MVP extensions.
EXT-RF-LANG-01 is an approved cross-cutting `pt-BR` user-interface requirement
for existing, MVP, and later screens; implementation docs and prompts remain
English. All future UI tasks inherit it through `AGENTS.md` and
`docs/frontend-design.md`; Task 18 audits MVP coverage and Task 19 verifies it.
The repository-managed Keycloak `academia` theme now provides the shared visual
and Portuguese presentation for login and first-access screens. It is a
cross-cutting authentication presentation integration, not a retroactive change
to the historical scopes of Tasks 02, 06, or 08. Task 19 still verifies the
integrated EXT-CA-LANG-01.4 journey.

The approved architecture remains a React/TypeScript/Vite/MUI frontend,
Python/FastAPI modular monolith, PostgreSQL with SQLAlchemy/Alembic, Keycloak
OIDC, REST/JSON/OpenAPI, SMTP/Mailpit adapter, provider-independent AI adapters,
and Docker Compose. No extension authorizes another backend, database, broker,
vector database, WebSocket layer, or social framework.

## Dependency chain

```text
foundation
  → authentication → authorization
  → local account/client → profile/status
  → Keycloak client provisioning + first access
  → invitation → shared frontend design system + existing UI restyle
  → secure link → structured onboarding
  → conversational onboarding → completion
  → training version lifecycle → initial generation
  → own current-plan view → own-context AI chat → approved adaptation
  → MVP visual polish → MVP end-to-end verification
  → post-MVP progress sharing / equipment catalog
  → anonymous occupancy → opt-in named presence
  → nonfinancial administrative dashboard
  → equipment-aware AI adaptation
  → social client profile and post interactions
```

The secure-link/form path and conversational path share one authoritative
structured onboarding and coexist unless a later approved decision replaces
one. Client-owned APIs resolve `Keycloak sub → Account → Client` and never use a
browser-provided client ID as proof of ownership.

## Dependency-ordered batches

1. **Foundation (Task 01, completed):** approved workspace/runtime/test baseline.
2. **Identity and clients (Tasks 02–06, completed):** authentication,
   authorization, local client/account behavior, lifecycle, Keycloak
   provisioning, client-only role, first access, and reconciliation.
3. **Visual foundation (Task 08, completed):** shared MUI theme, primitives,
   ClientShell/AdminShell, and retroactive restyling of frontend work from
   completed Tasks 01–07; no change to their historical business scope.
   The later Keycloak `academia` theme extends this visual system to the
   server-rendered authentication experience without changing its OIDC flow.
4. **Onboarding (Tasks 07 and 09–12 completed):**
   invitation, secure form access, authoritative structured health data,
   conversational AI orchestration, and shared completion using Task 08 UI
   foundations.
5. **Training and client AI (Tasks 13–17, completed):** version lifecycle, initial
   generation, mobile personal plan, client-facing chat, approved adaptation.
6. **MVP visual polish (Task 18, completed):** consistency, responsiveness,
   loading/empty/error states, copy, and accessibility after major MVP UI.
7. **MVP verification (Task 19, functional report present; manual/external RNF
   evidence pending):** original MVP plus EXT-RF-AI-01, including client
   identity and cross-client isolation.
8. **Post-MVP client modules (Tasks 20–21, implemented):** controlled progress
   sharing and equipment management/catalog/quantity.
9. **Occupancy and privacy-gated presence (Tasks 22–23, implemented):**
   anonymous count first; named presence separately and only with opt-in.
10. **Validated gap remediation (Tasks 24–25 implemented):**
    nonfinancial administrative indicators followed by the Task 21
    equipment-catalog constraint on Task 17 AI adaptation.
11. **Social profile expansion (Task 26 planned):** redesign the individual
    profile over Tasks 20 and 23 with default-on authenticated visibility,
    owner-managed picture/nickname/biography, following, bounded likes/comments,
    moderation, and a stable boundary for a separately approved future feed.

Post-MVP order is an implementation dependency/order, not a change to original
MVP membership. RF-14 is now revalidated as already available through the
authenticated own-onboarding read path and completed read-only form. Remaining
RF-06–RF-08, RF-20–RF-22, and RF-26–RF-31 require an approved prompt or an
explicit exclusion before implementation.

## Decision gates

| Decision | Status and affected tasks |
| --- | --- |
| DEC-01 | Unresolved/non-blocking while the original catalog and MVP are preserved. |
| DEC-02 | Resolved: the historical X suffix is removed; use RF-24/RF-25. |
| DEC-03 | Resolved; inherited architecture baseline for every task. |
| DEC-04 | Resolved for current roles/provisioning; inherited by authorization, health, training, and future employee work. |
| DEC-05 | Resolved; CA-03.4 remains deferred to RF-22 and is not satisfied. |
| DEC-06 | Invitation-token policy is resolved for Tasks 07 and 09; schema, validation, and editable-draft behavior are resolved for Task 10. Recovery-token policy remains unresolved for later affected work. |
| DEC-07 | Resolved for Tasks 13–17: instructor-only approval/activation and no automatic health-risk generation block; Task 17 applies the lifecycle to client-confirmed proposals. |
| DEC-08 | Resolved for Tasks 11, 14, 16, and 17: OpenAI Responses API behind a provider-neutral adapter, bounded context, timeout/retry, and structured output where applicable; Ollama is also available as a local development/test adapter. Task 16 uses plain conversational output only and has no plan-mutation authority; Task 17 uses structured output only after explicit client confirmation. |
| DEC-09 | Resolved for biometric recognition/enrollment: measured >=95% configured-system precision, calibrated provider threshold, minimized references, safe replacement, retention, and non-sensitive audit. Task 22 still does not consume biometric data. |
| DEC-10 | Resolved for Task 22: client confirmed-passage ledger is authoritative; cameras are deferred, auxiliary, coverage-declared 60-second-fresh observations only. |
| DEC-11 | Resolved for approved boundaries: confirmed-passage events use opaque client references resolved privately to local Clients, alongside the occupancy contract, provider-neutral facial recognition, and idempotent external release request. Turnstile actuation and physical passage remain external; DEC-10 alone governs occupancy. |
| DEC-12–DEC-14 | Blocking future plan/payment/financial/class tasks respectively. |
| DEC-15 | Resolved for Task 17's recognized-exercise candidate and instructor-review scope. Task 21 remains the catalog boundary. |
| DEC-16 | Resolved for personal-use MVP verification: bounded single-user load, representative viewport/usability/accessibility checks, eight-hour local soak, restart recovery, failure isolation, and maintainability/integration evidence. Task 19 formal RNF sign-off may proceed. |
| DEC-17 | Resolved for Account↔Client identity; later domain slices must resolve their own unsettled models before migrations. |
| DEC-18 | Health/onboarding policy is resolved for Task 10; Task 11 has five-day onboarding-chat retention and Task 16 has separate client-only training-chat/summary retention of 30 days. Biometric lifecycle is governed separately by DEC-09. |
| DEC-19 | Resolved: client-facing direction and four approved extension IDs. |
| EXT-DEC-SOC-01 | Resolved and implemented by Task 20: private-by-default author ownership, explicit shared visibility, and approved administrator moderation/deletion. |
| EXT-DEC-SOC-02 | Resolved for Task 26: default-on authenticated social profiles, optional nickname/biography and managed image, unilateral following, likes/comments, moderation/erasure, and no current feed. |
| EXT-DEC-EQP-01 | Resolved for Task 21: UUID-identified logical models, physical units, and derived active quantity without availability semantics. |
| EXT-DEC-PRES-01 | Resolved for Task 23: client-owned default-off profile tag, fresh confirmed-passage derivation, immediate opt-out, and no directory. |

## Task index

| # | Task | Requirement ownership/integration | Prerequisites | Scope | Result |
| --- | --- | --- | --- | --- | --- |
| 01 | Project foundation | Enabler | None | Completed | Approved runnable/testable skeleton |
| 02 | Authentication | RF-04 | 01 | Completed | Active identities authenticate; anonymous access rejected |
| 03 | Authorization | RF-05 | 02 | Completed | Backend role/policy boundaries |
| 04 | Client registration and search | RF-01, RF-02 | 01–03 | Completed | Local Account/Client creation and admin search |
| 05 | Client profile and status | RF-03 except deferred CA-03.4 | 04 | Completed reduced scope | Updates, active state, history preservation |
| 06 | Client identity provisioning | RF-01/RF-04/RF-05 integration | 02–05 | Completed | Client-only Keycloak identity, subject linkage, first access, independent durable reconciliation |
| 07 | Onboarding invitations | RF-09 | 03, 04, 06; approved DEC-06 token policy | Completed | Client-bound e-mail invitation outcome |
| 08 | Frontend design system and existing UI restyle | Visual enabler; no new RF ownership | 01–07 | Completed | Shared MUI tokens/primitives/shells; retroactive UI restyle |
| 09 | Secure onboarding access | RF-10 | 07, 08; DEC-06 | Completed | Valid scoped onboarding entry and intentional token redemption |
| 10 | Physical and health onboarding | RF-11, RF-12 | 03, 08, 09; DEC-06/18 | Completed | Client-scoped structured draft, separated health data, validation, and audit metadata |
| 11 | Conversational AI onboarding | EXT-RF-AI-01 | 06, 08, 10; DEC-06/08/18 | Completed | Client-only resumable AI interview, final validated extraction, and bounded retention |
| 12 | Onboarding completion | RF-13 | 10, 11; DEC-06 | Completed | Shared validation with intentional atomic completion and timestamp |
| 13 | Training version lifecycle | RF-17 | 03, 12; DEC-07/15/17 | Completed | Immutable versions/current/professional attribution and manual proposal path |
| 14 | Initial AI training generation | RF-15; RF-17 integration | 12, 13; DEC-07/08/15/18 | Completed + follow-up | Client-triggered, completed-onboarding-scoped generation that reuses the sole client proposal regardless of origin; instructor review required |
| 15 | Current training view | RF-16; RF-17 integration | 06, 08, 13, 14 | Completed | Mobile own-current-plan/exercise view with empty/loading/error states |
| 16 | AI assistant chat | RF-18 | 06, 08, 14, 15; DEC-08/18 | Completed + follow-up | Client-only 30-day persisted assistant; may refine only the sole client draft, regardless of creator, through validated structured output |
| 17 | Dynamic training adaptation | RF-19; RF-17 integration | 08, 13, 16; DEC-07/08/15 | Completed | AI-detected, client-confirmed structured proposals, instructor review, immutable current version, history preserved |
| 18 | MVP frontend visual polish | Visual enabler; no new RF ownership | 08–17 | Completed | Shared consistency, responsive, accessibility, loading/empty/error, and pt-BR copy pass; Task 19 retains end-to-end verification. |
| 19 | MVP end-to-end verification | All original MVP + EXT-RF-AI-01 verification | 02–18; DEC-16 for formal RNF | Functional report present; manual/external RNF evidence pending | Traceable critical journey/security evidence plus remaining DEC-16 checks |
| 20 | Controlled progress sharing | EXT-RF-SOC-01 | 03, 06, 08; EXT-DEC-SOC-01 | Implemented | Author-owned private/shared updates with approved moderation and erasure behavior |
| 21 | Equipment catalog and quantities | RF-32, RF-33, EXT-RF-EQP-01 | 03, 06, 08; EXT-DEC-EQP-01 | Implemented | Admin model/unit lifecycle, public active catalog, and derived total by type/model |
| 22 | Anonymous gym occupancy | RF-23–RF-25; RN-37 boundary | 03, 06, 08; resolved Task 22 DEC-10/11 boundary | Implemented | Private confirmed-passage/correction ledger, source-health status, and privacy-safe current client count/mobile display |
| 23 | Opt-in profile presence | EXT-RF-PRES-01 | 06, 08, 22; resolved EXT-DEC-PRES-01 | Implemented | Consent-based individual profile status tag; no directory |
| 24 | Nonfinancial administrative dashboard | RF-28 CA-28.1/CA-28.3; RF-29 CA-29.1 | 03, 04, 06, 08, 22 | Implemented (nonfinancial partial) | Admin-only active-client, confirmed-entry history, and current occupancy aggregates; no financial scope |
| 25 | Equipment-aware AI training adaptation | RF-19 integration with RF-32/RF-33 and EXT-RF-EQP-01 | 17, 21; DEC-07/08/15; EXT-DEC-EQP-01 | Implemented | Canonical active EquipmentModel references constrain machine-dependent AI candidates without live-availability semantics |
| 26 | Social client profile and post interactions | EXT-RF-SOC-02; integration with EXT-RF-SOC-01/EXT-RF-PRES-01 | 06, 08, 20, 23; EXT-DEC-SOC-01/02; EXT-DEC-PRES-01 | Planned | Default-on authenticated social profile, managed picture/nickname/bio, follow graph, post detail likes/comments, moderation, erasure, and future-feed boundary |

## Completed-task history and later impact

Tasks 01–07 retain the scope that was actually implemented. They are not
rewritten as owners of later client-facing features:

- Tasks 02–03 established authentication/authorization; Task 06 subsequently
  supplied real provisioned client identities and verified client-role denial.
- Tasks 04–05 own local client/account CRUD and active-state behavior; they did
  not implement conversational onboarding, social, equipment, or presence.
- Task 06 owns the later-approved Keycloak provisioning integration and is now a
  prerequisite for every authenticated client task.
- Task 07 owns invitations; Task 08 restyles its frontend alongside other
  completed screens without retroactively changing Task 07 behavior.
- Task 08 owns the completed shared MUI design foundation and restyle. Task 09
  owns completed secure, client-scoped invitation-token access; neither task
  implements the physical/health onboarding schema or completion flows.
- CA-03.4 remains deferred and must not be reported as implemented.

No future task may assume a database client has a usable login unless Task 06
provisioning or its explicit reconciliation completed.

## Coverage and reproducibility checks

- Original MVP ownership remains complete: RF-04 (02), RF-05 (03), RF-01/RF-02
  (04), RF-03 reduced scope (05), RF-09 (07), RF-10 (09), RF-11/RF-12 (10),
  RF-13 (12), RF-17 (13), RF-15 (14), RF-16 (15), RF-18 (16), RF-19 (17).
- EXT-RF-AI-01 is owned by Task 11 and integration-verified in Task 19.
- EXT-RF-SOC-01, EXT-RF-EQP-01, and EXT-RF-PRES-01 are implemented by Tasks
  20, 21, and 23 respectively. EXT-RF-SOC-02 is planned by Task 26 and does not
  retroactively expand Task 20.
- RF-32/RF-33 remain original requirements; only quantity is an extension.
- RF-24/RF-25 anonymous count is separate from EXT-RF-PRES-01 named presence.
- Every authenticated client task depends directly or transitively on Task 06
  and requires server-side identity resolution.
- Every future UI task uses `docs/frontend-design.md` and Task 08 shared
  foundations; Task 18 has polished the integrated MVP before Task 19 verifies it.
- Existing and future public, client, and admin UI must meet EXT-RF-LANG-01;
  Keycloak-hosted screens shown to users require Portuguese too. Historical
  completed task scope is not rewritten to claim this was already verified.
- Task 08 covers existing authentication, authorization states, client
  registration/search/details/profile/status/provisioning, invitation, shells,
  navigation, forms, dialogs, loading/error/empty states, and feedback without
  changing backend behavior or API contracts.
- Future onboarding, training, AI chat, progress, equipment, occupancy, and
  presence UIs share the visual system while maintaining mobile/accessibility
  requirements and separate admin/client density.
- A clean implementation run stops at unresolved blocking decisions instead of
  silently inventing onboarding, AI, social, equipment, occupancy, or privacy
  models.

## Next executable task

### Evidence-qualified prescription follow-up — specification, 2026-10-22

The owner requested the planning sequence below to research prescription evidence,
download/vectorize eligible material, and discard unsupported AI-generated
workouts. Canonical scope: EXT-RF-AI-02 and EXT-DEC-AI-02 in requirements.md.
See [feature specification](evidence-qualified-training-specification.md).
Task 45 prespecifies the [methodological protocol](training-evidence-methodology.md);
Tasks 47 and 51 consume its appraisal, evidence-to-decision and independent
evaluation records. Scientific criteria, technical constraints and product
release policies remain distinct under EXT-CA-AI-02.14.
Task 45's bounded research/documentation is delivered in the
[source review](training-evidence-source-review.md); independent human appraisals
and named governance remain pending. Task 46's bounded acquisition and real
indexing are verified; Task 47 has draft contracts and a technical retrieval
probe. The owner-approved sequencing exception now permits isolated Tasks 48–50
development; their validator, lifecycle harness and reusable UI are tested.
Operational integration is implemented; final-layout expansion indexing and
PostgreSQL migration are verified. Independent evaluation and release remain pending. See the
[execution status](tasks/51-training-prescription-verification-report.md).
No professional policy or release is approved; older pending work stays open.

| Task | Feature task | Scope | Prerequisites | Status |
| --- | --- | --- | --- | --- |
| [45](tasks/45-training-evidence-discovery.md) | EVID-IMPL-01 | Source discovery, license screening and coverage gaps | Existing knowledge/onboarding/training inspection | Research delivered; human appraisal/governance pending |
| [46](tasks/46-training-evidence-ingestion.md) | EVID-IMPL-02 | Actual eligible downloads, extraction and vectorization | 45 eligible subset | Expanded 66-vector corpus indexed; unchanged second run and nine technical topic queries verified |
| [47](tasks/47-training-prescription-policies.md) | EVID-IMPL-03 | Professionally reviewed computable prescription rules | 45–46; professional decisions for enabled cohorts | Draft schemas/probe and in-app instructor judgments/custody implemented; actual approvals/feasibility/seal pending |
| [48](tasks/48-training-prescription-evidence-gate.md) | EVID-IMPL-04 | Applicable retrieval, coverage checks and validation trace | 46–47; approved isolated-development exception | Shared core and operational adapters implemented; PostgreSQL migration verified; enablement pending |
| [49](tasks/49-training-generation-abstention.md) | EVID-IMPL-05 | Shared atomic generation/abstention gate on all prescriptive paths | 48 | Operational generation/chat/adaptation/review integration implemented; real-provider evaluation pending |
| [50](tasks/50-training-evidence-review-ui.md) | EVID-IMPL-06 | Client abstention and instructor evidence-review UX | 49; established frontend design | Production views and instructor review/custody workspace connected; browser and intended-user review pending |
| [51](tasks/51-training-prescription-verification.md) | EVID-IMPL-07 | Independent evaluation and limited release report | 45–50; professional evaluation decisions | Status report delivered; independent operational evaluation/release unexecuted |

Research/eligible acquisition can proceed without invented clinical rules.
Unapproved or unmeasured profiles remain unsupported. Follow each task's gates;
no commit/push or professional approval is implied.

### Prescription remediation specification — 2026-10-24

**Implementation update — 2026-10-25:** the owner waived independent evaluator/
held-out-case prerequisites for assisted RAG. The owner-authorized mode now has a
successful actual local retrieval/writer/reviewer run and an outage control.
See the [delivery and exact scope](tasks/46-59-owner-rag-delivery.md). Compiled
clinical qualification is separate; manual browser QA remains unexecuted.

The owner requested a specific specification for the rejected-sheet and approved-
rule test failures. Canonical scope: EXT-CA-AI-02.26–33, refining RF-15/RF-18/RF-19.
The [remediation specification](training-prescription-remediation-spec.md) supplies
the incident matrix, contracts, decision gates and concrete verification cases.
This is planned work, not a claim that the policies or release are complete.
The later owner source/rule approval amendment governs that approval scope;
historical professional-review-only descriptions above remain historical context.

| Task | Feature task | Deliverable | Dependencies | Status |
| --- | --- | --- | --- | --- |
| 52 | PRES-REM-01 | Executable-policy inventory, coherent branches and truthful approval basis | Existing 45–51 artifacts; exact owner decision | Compiler/readiness/owner authorization implemented; clinical bundle publication remains separate |
| 53 | PRES-REM-02 | Versioned exercise identities and supported modality representation | 52 scope/branch definitions | Typed modes and round trips implemented; twelve stable free-exercise IDs used by assisted RAG |
| 54 | PRES-REM-03 | Authoritative load, progression and modality accounting calculations | 52–53 contracts | Decimal accounting/calculations implemented; five observed wrong quantities have regression oracles |
| 55 | PRES-REM-04 | Constrained writer schema and representation-only adapters | 52–54 envelope | Strict/scoped schemas and deterministic ID/alias rendering implemented; actual local run passes |
| 56 | PRES-REM-05 | Exact bounds, interruption/regression and clarification actions | 52–55 | Open/exclusive bounds, stop/regress, authority and field feedback implemented/tested |
| 57 | PRES-REM-06 | Applicable branch/rule/exercise/passage selection | 52–56; existing knowledge filters | Scoped rules/IDs and whole-passage context budgeting implemented; maximum six preserved |
| 58 | PRES-REM-07 | Single correction, shared budgets and atomic lifecycle integration | 52–57 | Shared 4/4/2 budgets, deadlines, correction, revalidation and atomic persistence implemented |
| 59 | PRES-REM-08 | Failure regressions, genuine positive paths, bounded model runs and release evidence | 52–58 for complete operational cases | Offline and exposed actual-model checks executed; owner RAG authorization replaces independent-release prerequisite for that mode |

Offline harness and baseline tests for 59 may be prepared alongside 52. End-to-end
completion and release depend on finished executable contracts and the existing
evaluation/release gates. No automatic implementation, model change, commit or
push is authorized by this planning entry.

### Earlier facial-access execution checkpoint

The user explicitly selected the controlled facial-access pilot as the next
implementation sequence. See [specification](facial-access-specification.md).
Historical task coverage above is not a claim that unrelated planned work should
be performed during this feature.

| Task | Feature task | Scope | Status |
| --- | --- | --- | --- |
| 38 | FACE-IMPL-01 | Canonical policy, free-use provider artifacts, pinned Docker preflight | Complete |
| 39 | FACE-IMPL-02 | Protected enrollment, staging and cleanup | Complete |
| 40 | FACE-IMPL-03 | Mandatory registration, shared enrollment, capture UI and erasure | Complete |
| 41 | FACE-IMPL-04 | Recognition, entry/exit policy and simulated release | Complete |
| 42 | FACE-IMPL-05 | Confirmed passages, state corrections and occupancy | Complete |
| 43 | FACE-IMPL-06 | Acesso facial admin workspace and integrated UI | Complete |
| 44 | FACE-IMPL-07 | Authorized reset and owner-only integrated verification | In progress — reset complete; owner webcam checks pending |

Complete/test/review/commit each task before proceeding. Stop for unforeseen
functional decisions; never claim owner webcam validation or population precision
based on fixture tests.
