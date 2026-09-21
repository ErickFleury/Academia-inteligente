# Academia Inteligente Implementation Plan

## Specification and architecture envelope

`docs/requirements.md` is the primary consolidated implementation
specification. `requirements.md` preserves the original 33 RFs, their CA, 6
RNFs, 37 RN, 10 TEC entries, original MVP, and DEC questions.
`docs/decisions.md` is the chronological decision authority, while
`docs/product-extensions.md` owns approved behavior added beyond the original
source. An unresolved conflict stops only the affected task.

The original MVP remains RF-01–RF-05, RF-09–RF-13, and RF-15–RF-19. DEC-19
adds EXT-RF-AI-01 conversational onboarding to the planned MVP experience; it
does not rewrite the historical MVP. EXT-RF-SOC-01, EXT-RF-EQP-01, and
EXT-RF-PRES-01 are approved post-MVP extensions.

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
  → invitation → secure link → structured onboarding
  → conversational onboarding → completion
  → training version lifecycle → initial generation
  → own current-plan view → own-context AI chat → approved adaptation
  → MVP end-to-end verification
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
3. **Onboarding (Task 07 completed; Tasks 08–11 future):** invitation and
   secure form access, authoritative structured health data, conversational AI
   orchestration, and shared completion.
4. **Training and client AI (Tasks 12–16, future):** version lifecycle, initial
   generation, mobile personal plan, client-facing chat, approved adaptation.
5. **MVP verification (Task 17, future):** original MVP plus EXT-RF-AI-01,
   including client identity and cross-client isolation.
6. **Post-MVP client modules (Tasks 18–19, future):** controlled progress
   sharing and equipment management/catalog/quantity.
7. **Occupancy and privacy-gated presence (Tasks 20–21, future):** anonymous
   count first; named presence separately and only with opt-in decisions.

Post-MVP order is an implementation dependency/order, not a change to original
MVP membership. Independent future RF-06–RF-08, RF-14, RF-20–RF-22, and
RF-26–RF-31 require their own tasks when prioritized.

## Decision gates

| Decision | Status and affected tasks |
| --- | --- |
| DEC-01 | Unresolved/non-blocking while the original catalog and MVP are preserved. |
| DEC-02 | Unresolved; relevant to Task 20 naming/traceability. |
| DEC-03 | Resolved; inherited architecture baseline for every task. |
| DEC-04 | Resolved for current roles/provisioning; inherited by authorization, health, training, and future employee work. |
| DEC-05 | Resolved; CA-03.4 remains deferred to RF-22 and is not satisfied. |
| DEC-06 | Invitation-token policy resolved for Task 07; schema, validation, and editability remain blocking for Tasks 08–11. |
| DEC-07 | Blocking Tasks 12, 13, and 16: severity and review/approval lifecycle. |
| DEC-08 | Blocking Tasks 10, 13, 15, and 16: AI provider/contract/context/failures. |
| DEC-09 | Blocking future biometric work and relevant Task 20 physical-access inputs. |
| DEC-10 | Blocking Task 20 and Task 21: occupancy sources/meaning/freshness. Do not infer a source of truth. |
| DEC-11 | Blocking Task 20 where external/access events are its inputs. |
| DEC-12–DEC-14 | Blocking future plan/payment/financial/class tasks respectively. |
| DEC-15 | Blocking Tasks 12, 13, and 16 wherever manual/professional/audit flows are required. |
| DEC-16 | Blocking formal RNF sign-off in Task 17. |
| DEC-17 | Resolved for Account↔Client identity; later domain slices must resolve their own unsettled models before migrations. |
| DEC-18 | Blocking Tasks 09, 10, 13, 15 and future biometric work: sensitive-data access/retention/logging. |
| DEC-19 | Resolved: client-facing direction and four approved extension IDs. |
| EXT-DEC-SOC-01 | Blocking Task 18 audience/moderation/deletion/retention model. |
| EXT-DEC-EQP-01 | Blocking Task 19 persistence/grouping model. |
| EXT-DEC-PRES-01 | Blocking Task 21 consent/source/fields/revocation/retention model. |

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
| 08 | Secure onboarding access | RF-10 | 07; DEC-06 | MVP future | Valid scoped link/form entry |
| 09 | Physical and health onboarding | RF-11, RF-12 | 03, 08; DEC-06/18 | MVP future | Authoritative structured onboarding draft |
| 10 | Conversational AI onboarding | EXT-RF-AI-01 | 06, 09; DEC-06/08/18 | MVP extension | Resumable AI orchestration over structured data |
| 11 | Onboarding completion | RF-13 | 09, 10; DEC-06 | MVP future | Shared validated completion/readiness |
| 12 | Training version lifecycle | RF-17 | 03, 11; DEC-07/15/17 | MVP future | Immutable versions/current/professional attribution |
| 13 | Initial AI training generation | RF-15; RF-17 integration | 11, 12; DEC-07/08/15/18 | MVP future | Safe structured proposal through lifecycle |
| 14 | Current training view | RF-16; RF-17 integration | 06, 12, 13 | MVP future | Mobile own-current-plan/exercise view |
| 15 | AI assistant chat | RF-18 | 06, 13, 14; DEC-08/18 | MVP future | Own-context read-only training assistant |
| 16 | Dynamic training adaptation | RF-19; RF-17 integration | 12, 15; DEC-07/08/15 | MVP future | Approved new version, history preserved |
| 17 | MVP end-to-end verification | All original MVP + EXT-RF-AI-01 verification | 02–16; DEC-16 for formal RNF | MVP verification | Traceable critical journey/security/RNF evidence |
| 18 | Controlled progress sharing | EXT-RF-SOC-01 | 03, 06; EXT-DEC-SOC-01 | Post-MVP extension | Author-owned private/shared updates |
| 19 | Equipment catalog and quantities | RF-32, RF-33, EXT-RF-EQP-01 | 03, 06; EXT-DEC-EQP-01 | Original post-MVP + extension | Admin catalog and active total by type/model |
| 20 | Anonymous gym occupancy | RF-23–RF-25X; RN-37 boundary | 03, 06 plus access inputs; DEC-10/11 | Original post-MVP, blocked | Privacy-safe current count/mobile display |
| 21 | Opt-in visible presence | EXT-RF-PRES-01 | 06, 20; DEC-10/EXT-DEC-PRES-01 | Post-MVP extension, blocked | Consent-based minimal named presence |

## Completed-task history and later impact

Tasks 01–06 retain the scope that was actually implemented. They are not
rewritten as owners of later client-facing features:

- Tasks 02–03 established authentication/authorization; Task 06 subsequently
  supplied real provisioned client identities and verified client-role denial.
- Tasks 04–05 own local client/account CRUD and active-state behavior; they did
  not implement conversational onboarding, social, equipment, or presence.
- Task 06 owns the later-approved Keycloak provisioning integration and is now a
  prerequisite for every authenticated client task.
- CA-03.4 remains deferred and must not be reported as implemented.

No future task may assume a database client has a usable login unless Task 06
provisioning or its explicit reconciliation completed.

## Coverage and reproducibility checks

- Original MVP ownership remains complete: RF-04 (02), RF-05 (03), RF-01/RF-02
  (04), RF-03 reduced scope (05), RF-09 (07), RF-10 (08), RF-11/RF-12 (09),
  RF-13 (11), RF-17 (12), RF-15 (13), RF-16 (14), RF-18 (15), RF-19 (16).
- EXT-RF-AI-01 is owned by Task 10 and integration-verified in Task 17.
- EXT-RF-SOC-01, EXT-RF-EQP-01, and EXT-RF-PRES-01 have explicit future owners.
- RF-32/RF-33 remain original requirements; only quantity is an extension.
- RF-24X/RF-25X anonymous count is separate from EXT-RF-PRES-01 named presence.
- Every authenticated client task depends directly or transitively on Task 06
  and requires server-side identity resolution.
- A clean implementation run stops at unresolved blocking decisions instead of
  silently inventing onboarding, AI, social, equipment, occupancy, or privacy
  models.

## Next executable task

Task 07 is next in dependency order. Its token-policy prerequisite is approved;
use the Terra/Medium prompt at the end of
`docs/tasks/07-onboarding-invitations.md`.
