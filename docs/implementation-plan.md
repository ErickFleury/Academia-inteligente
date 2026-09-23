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
does not rewrite the historical MVP. EXT-RF-SOC-01, EXT-RF-EQP-01, and
EXT-RF-PRES-01 are approved post-MVP extensions.
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
7. **MVP verification (Task 19, future):** original MVP plus EXT-RF-AI-01,
   including client identity and cross-client isolation.
8. **Post-MVP client modules (Tasks 20–21, future):** controlled progress
   sharing and equipment management/catalog/quantity.
9. **Occupancy and privacy-gated presence (Tasks 22–23, future):** anonymous
   count first; named presence separately and only with opt-in decisions.

Post-MVP order is an implementation dependency/order, not a change to original
MVP membership. Independent future RF-06–RF-08, RF-14, RF-20–RF-22, and
RF-26–RF-31 require their own tasks when prioritized.

## Decision gates

| Decision | Status and affected tasks |
| --- | --- |
| DEC-01 | Unresolved/non-blocking while the original catalog and MVP are preserved. |
| DEC-02 | Unresolved; relevant to Task 22 naming/traceability. |
| DEC-03 | Resolved; inherited architecture baseline for every task. |
| DEC-04 | Resolved for current roles/provisioning; inherited by authorization, health, training, and future employee work. |
| DEC-05 | Resolved; CA-03.4 remains deferred to RF-22 and is not satisfied. |
| DEC-06 | Invitation-token policy is resolved for Tasks 07 and 09; schema, validation, and editable-draft behavior are resolved for Task 10. Recovery-token policy remains unresolved for later affected work. |
| DEC-07 | Resolved for Tasks 13–17: instructor-only approval/activation and no automatic health-risk generation block; Task 17 applies the lifecycle to client-confirmed proposals. |
| DEC-08 | Resolved for Tasks 11, 14, 16, and 17: OpenAI Responses API behind a provider-neutral adapter, bounded context, timeout/retry, and structured output where applicable; Ollama is also available as a local development/test adapter. Task 16 uses plain conversational output only and has no plan-mutation authority; Task 17 uses structured output only after explicit client confirmation. |
| DEC-09 | Blocking future biometric work and relevant Task 22 physical-access inputs. |
| DEC-10 | Blocking Task 22 and Task 23: occupancy sources/meaning/freshness. Do not infer a source of truth. |
| DEC-11 | Blocking Task 22 where external/access events are its inputs. |
| DEC-12–DEC-14 | Blocking future plan/payment/financial/class tasks respectively. |
| DEC-15 | Resolved for Task 17's recognized-exercise candidate and instructor-review scope. Task 21 remains the catalog boundary. |
| DEC-16 | Resolved for personal-use MVP verification: bounded single-user load, representative viewport/usability/accessibility checks, eight-hour local soak, restart recovery, failure isolation, and maintainability/integration evidence. Task 19 formal RNF sign-off may proceed. |
| DEC-17 | Resolved for Account↔Client identity; later domain slices must resolve their own unsettled models before migrations. |
| DEC-18 | Health/onboarding policy is resolved for Task 10; Task 11 has five-day onboarding-chat retention and Task 16 has separate client-only training-chat/summary retention of 30 days. Biometric behavior still gates affected work. |
| DEC-19 | Resolved: client-facing direction and four approved extension IDs. |
| EXT-DEC-SOC-01 | Blocking Task 20 audience/moderation/deletion/retention model. |
| EXT-DEC-EQP-01 | Blocking Task 21 persistence/grouping model. |
| EXT-DEC-PRES-01 | Blocking Task 23 consent/source/fields/revocation/retention model. |

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
| 19 | MVP end-to-end verification | All original MVP + EXT-RF-AI-01 verification | 02–18; DEC-16 for formal RNF | MVP verification | Traceable critical journey/security/RNF evidence |
| 20 | Controlled progress sharing | EXT-RF-SOC-01 | 03, 06, 08; EXT-DEC-SOC-01 | Post-MVP extension | Author-owned private/shared updates |
| 21 | Equipment catalog and quantities | RF-32, RF-33, EXT-RF-EQP-01 | 03, 06, 08; EXT-DEC-EQP-01 | Original post-MVP + extension | Admin catalog and active total by type/model |
| 22 | Anonymous gym occupancy | RF-23–RF-25X; RN-37 boundary | 03, 06, 08 plus access inputs; DEC-10/11 | Original post-MVP, blocked | Privacy-safe current count/mobile display |
| 23 | Opt-in visible presence | EXT-RF-PRES-01 | 06, 08, 22; DEC-10/EXT-DEC-PRES-01 | Post-MVP extension, blocked | Consent-based minimal named presence |

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
- EXT-RF-SOC-01, EXT-RF-EQP-01, and EXT-RF-PRES-01 have explicit future owners.
- RF-32/RF-33 remain original requirements; only quantity is an extension.
- RF-24X/RF-25X anonymous count is separate from EXT-RF-PRES-01 named presence.
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

Task 19, MVP end-to-end verification, is next in dependency order. It verifies
the integrated MVP after the Task 18 visual polish without changing established
business behavior.
