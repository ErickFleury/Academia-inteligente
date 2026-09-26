# Requirements Coverage Review

This review answers one question: which documented functionality from the
original project specification still lacks implementation or a complete task
path? It is a requirements-to-task coverage review, not a final code-quality or
architecture audit.

The source of original requirements is `docs/requirements.md`, which explicitly
identifies 33 original RFs, 110 functional acceptance criteria, six RNFs with
18 acceptance criteria, 37 original business rules, and ten original technology
entries. `REQUISITOS.md` is not present in the repository or its visible Git
history, so it could not be read; this review follows the later instruction to
treat `docs/requirements.md` as canonical.

Evidence reviewed: `docs/requirements.md`, `docs/decisions.md`,
`docs/implementation-plan.md`, every file under `docs/tasks/`,
`docs/product-extensions.md`, the UI-relevant parts of
`docs/frontend-design.md`, Task 19's verification report, and narrow repository
status/history checks needed to resolve task-status inconsistencies.

Repository-state caveat: before this review began, the worktree already
contained uncommitted Task 23 implementation and documentation changes. This
review preserves those changes and creates only this file. Accordingly, the
final `git status` cannot truthfully show this file as the repository's only
overall change; it is the only change introduced by this review.

There are also status inconsistencies in the planning documents:

- Task 19 has a verification report and automated evidence, although the
  implementation plan still calls it “future” and the next executable task.
- Controlled progress sharing exists in commit `de330ab`, although the
  canonical status table still calls EXT-RF-SOC-01 planned and Task 20 has no
  explicit completion marker.
- The current worktree marks Tasks 21–23 implemented, while some older status
  prose in `docs/requirements.md` still calls Task 23 blocked.

Where those inconsistencies affect certainty, this report uses **NEEDS
VERIFICATION** rather than inferring completion from prose alone.

## A. Original requirements still missing from the task plan

These original requirements or criteria have no numbered task that owns their
implementation. Some are also blocked by unresolved decisions; section E
records those blockers separately.

| Original requirement | Missing task-plan coverage | Existing nearby work that must not be mistaken for coverage |
| --- | --- | --- |
| RF-06 / CA-06.1–CA-06.3 | No task owns recovery request, recovery token lifecycle, or successful post-recovery authentication. | Task 07 owns onboarding invitations, not account recovery. CA-06.4's local SMTP-container constraint is indirectly present through Mailpit/Docker Compose. |
| RF-07 / CA-07.1–CA-07.3 | No employee-registration task exists. Required employee data and local Employee↔Account persistence still need task-level definition. | DEC-04 defines roles and says a future administrative flow will provision employees; it does not implement that flow. |
| RF-08 / CA-08.1–CA-08.3 and RN-03 | No employee list/view/update/deactivate task exists. | Client management and Keycloak realm roles do not satisfy employee lifecycle management. |
| RF-14 / CA-14.1–CA-14.3 | No post-completion own-onboarding consultation task exists. | Tasks 10–12 cover editable drafts and completion; Task 12 expressly excludes RF-14. |
| RF-20 / CA-20.1, CA-20.2, CA-20.4 | No task owns ingestion of provider-neutral facial-recognition results and their idempotent logical recognition attempts. | Task 22 ingests **confirmed physical-passage** events. DEC-11 explicitly distinguishes these from recognition results. CA-20.3's external-turnstile boundary is approved in DEC-11, but the RF-20 recognition integration itself is absent. |
| RF-21 / CA-21.1–CA-21.4 and RN-06/RN-07 | No task owns facial identity resolution, unknown-identity denial, inactive-client denial in the recognition flow, or validation of the configured recognition system's measured precision. | Task 22 resolves an opaque passage reference after physical passage; that is not facial recognition or entry eligibility. |
| RF-22 / CA-22.1–CA-22.3, RN-10, RN-34, and RF-03/CA-03.4 dependency | No biometric-enrollment task exists for attendant-authorized capture, quality validation, safe replacement, provider reference lifecycle, and deletion. | DEC-09 resolves policy and recommends—but does not select—CompreFace for a pilot. Policy documentation is not implementation. |
| RF-26 / CA-26.1–CA-26.3 | No billing-record task exists. | Current account activity, client management, and progress data are unrelated. |
| RF-27 / CA-27.1–CA-27.3 | No authorized staff/client billing-status view task exists. | No existing client profile or admin page owns financial records. |
| RF-28 / CA-28.1–CA-28.3 | No administrative-dashboard task exists. | The current admin client-management screen is not the consolidated dashboard required by RF-28. |
| RF-29 / CA-29.1–CA-29.2 | No task owns the consolidated indicator screen. | Task 22 supplies current occupancy data, but no dashboard combines active clients, weekly attendance, occupancy, and eventual financial indicators. |
| RF-30 / CA-30.1–CA-30.3 and RN-25 | No class-schedule task exists. | No existing calendar, equipment, or progress UI covers class occurrences or their public/authenticated presentation. |
| RF-31 / CA-31.1 and RN-22 | No purchasable-plan/payment/enrollment task exists. | `account_active` deliberately does not represent payment, enrollment, or gym-entry eligibility. |
| RN-08 | No task owns the original mandatory alternative flow after facial-recognition failure. | DEC-09 permits one extra biometric attempt, and DEC-11 ends the current biometric flow without a manual bypass. Neither documents an implemented alternative flow satisfying RN-08. |
| RN-20 | No exercise-catalog lifecycle task owns active/inactive exercise selection while preserving historical plan references. | Task 21 is an equipment catalog and explicitly excludes exercise CRUD. Training items currently carrying exercise names are not an exercise lifecycle. |
| RN-21 | No evaluation workflow/task owns dated evaluations with an identifiable responsible person. | Onboarding and training-version timestamps do not create the evaluation concept referenced by RN-21. |
| RN-26 | No notice/notification task owns notices for critical permission, biometric, and configuration changes. | Existing UI feedback and audit metadata are not the notice behavior required by RN-26. |
| RN-27, uncovered portion | There is no system-wide audit/evidence task proving that actors cannot erase evidence of their own problematic actions across all applicable domains. | Onboarding, training, and progress implement selected audit/history controls; the later approved irreversible account-erasure exception intentionally removes all client-linked evidence. |
| RN-34 | No future biometric/report task is assigned responsibility for excluding biometric data from ordinary operational reports. | Current reports contain no biometrics because neither biometrics nor general reporting exists; that absence is not implementation evidence for the future flows. |
| TEC-03 / approved UFW constraint | No deployment/security task owns host-level UFW configuration, documented ports/rules, or verification. | Docker Compose service exposure is configured, but Task 01 explicitly placed firewall rules out of scope. |
| TEC-10, facial-integration portion | No task owns unit/integration/API-contract tests for the missing RF-20–RF-22 facial integration. | AI and implemented APIs have tests; facial-recognition contracts remain policy-only. |

The implementation plan itself acknowledges that RF-06–RF-08, RF-14,
RF-20–RF-22, and RF-26–RF-31 “require their own tasks when prioritized,” but no
such task files exist. They are therefore **MISSING FROM TASK PLAN**, not merely
scheduled later.

## B. Original requirements planned but not yet implemented

No unimplemented original functional feature has a complete numbered task ready
for execution. The only existing original-requirement task with unfinished work
is Task 19's formal RNF verification.

| Planned work | Existing task | Remaining work |
| --- | --- | --- |
| RNF01 performance sign-off | Task 19 | Run the approved approximately-50-client, ten-run measurements and three-request burst; verify at least nine runs under two seconds and browser-visible processing within 200 ms. |
| RNF02 usability sign-off | Task 19 | Complete the intended client, instructor, and administrator checklist without source-code consultation or step-by-step assistance. |
| RNF03 responsive sign-off | Task 19 | Perform live checks at 360×800, 768×1024, and 1366×768, including no ordinary smartphone horizontal scrolling. |
| RNF04 maintainability sign-off | Task 19 | Close or explicitly re-evaluate the report's repository-wide lint failure and complete the formal affected-suite/responsibility evidence. |
| RNF05 availability/recovery sign-off | Task 19 | Run the eight-hour one-minute health-check soak and normal-stack restart recovery within five minutes with no data loss/manual database repair. |

Task 19's report calls these evidence gaps rather than known product defects.
That distinction is retained here: their implementation status is **NEEDS
VERIFICATION**, but the original RNF acceptance criteria are not yet fully
satisfied.

## C. Original requirements only partially implemented

| Original requirement | Implemented portion | Missing or unverified portion | Status |
| --- | --- | --- | --- |
| RF-03 | Task 05 and Task 06 verify CA-03.1–CA-03.3: profile updates persist, inactive application accounts are rejected, and deactivation preserves history. | CA-03.4 biometric readiness is unsatisfied and depends on missing RF-22. | **PARTIAL** |
| RF-06 | CA-06.4 is indirectly covered by the isolated Mailpit SMTP container in the approved Docker Compose baseline. | CA-06.1–CA-06.3 recovery behavior has no task, and recovery-token policy remains unresolved. | **PARTIAL** |
| RF-20 | DEC-11 satisfies the architectural intent of CA-20.3: physical turnstile mechanics remain external. | No recognition-result endpoint implements CA-20.1, CA-20.2, or CA-20.4. The Task 22 passage endpoint has different semantics. | **PARTIAL POLICY ONLY; IMPLEMENTATION MISSING** |
| RN-18 | Immutable current/superseded plan versions preserve plan content through Tasks 13 and 17. | Completed-workout tracking is explicitly outside Task 13 and has no task, so the rule cannot be demonstrated against actual completed workouts. | **PARTIAL** |
| RN-27 | Selected onboarding, training, moderation, and integration actions preserve audit/history evidence. | There is no complete cross-domain audit ownership or verification, and account erasure is an approved explicit exception. | **PARTIAL** |
| RNF01 | Controlled external timeouts/errors and loading states exist; CA-RNF01.3 passed Task 19. | CA-RNF01.1 and the 200 ms part of CA-RNF01.2 remain unmeasured. | **PARTIAL / NEEDS VERIFICATION** |
| RNF02 | Shared navigation, labels, form validation, and automated UI tests provide partial CA-RNF02.1/.2 evidence. | Intended-user completion, including CA-RNF02.3, remains unverified. | **PARTIAL / NEEDS VERIFICATION** |
| RNF03 | Responsive MUI patterns and feature-level UI tests exist. | All three formal viewport criteria remain unverified in a live browser. | **PARTIAL / NEEDS VERIFICATION** |
| RNF04 | Modular services/adapters and regression tests provide partial evidence. | Task 19 did not complete clean repository-wide lint/formal maintainability sign-off. | **PARTIAL / NEEDS VERIFICATION** |
| RNF05 | CA-RNF05.2/.3 passed through controlled AI/e-mail failures and independent operation evidence. | CA-RNF05.1 and restart recovery remain unverified. | **PARTIAL / NEEDS VERIFICATION** |

RF-23 is not classified partial merely because there is no attendance-report
screen: its original acceptance criteria require client-linked, timestamped,
idempotent entry/exit persistence, which Task 22 covers. A new attendance UI
must not be invented without a requirement.

## D. Original requirements intentionally deferred

| Requirement | Status | Approved reason | Expected future task |
| --- | --- | --- | --- |
| RF-03 / CA-03.4 | **DEFERRED — APPROVED** | DEC-05 separates application activity from physical access and explicitly defers biometric-photo readiness to RF-22. | No task exists; should be owned by the recommended biometric-enrollment task. |
| RN-37 camera-based occupancy | **DEFERRED — APPROVED** | DEC-10 makes confirmed-passage events authoritative and defers cameras as auxiliary, zone-declared observations with 60-second freshness and no overwrite/blending. | No task exists; a future auxiliary-camera task is required only when prioritized. |
| RN-09 manual-release audit | **DEFERRED — APPROVED FOR THE CURRENT FLOW** | DEC-11 approves no manual biometric override or manual turnstile release inside the current application flow. If a manual bypass is later approved, actor and reason auditing becomes mandatory. | No current task; future manual-access task if approved. |
| RN-28 export authorization | **DEFERRED — APPROVED / CONDITIONAL** | DEC-15 records exports as future work. No original RF currently requires an export interface, but any future export must reuse screen/API permissions. | No task exists. |
| TEC-03 NestJS portion | **INTENTIONALLY CHANGED — APPROVED** | DEC-03 selects the Python/FastAPI modular monolith and gives NestJS no MVP responsibility. | None unless a later explicit architecture decision adds it. |
| TEC-05 authentication alternative | **INTENTIONALLY RESOLVED — APPROVED** | DEC-03 selects Keycloak/OIDC rather than backend-owned credentials. | Implemented by Tasks 02 and 06. |
| TEC-09 e-mail alternative | **INTENTIONALLY RESOLVED — APPROVED** | DEC-03 selects SMTP behind an adapter with Mailpit for local development. | Implemented by foundation/invitation work; recovery still needs its own task. |

Being outside the original MVP is not itself an approved cancellation. RF-06–
RF-08, RF-14, RF-20–RF-33 remain original requirements unless a decision
explicitly changes or defers them.

## E. Original requirements blocked by unresolved decisions

| Requirement | Unresolved decision | Blocked behavior |
| --- | --- | --- |
| RF-06 / CA-06.1–CA-06.3 | DEC-06, recovery-token portion | Token lifetime, issue/use/reuse/revocation rules, recovery outcome, and safe transition to the new credential mechanism. |
| RF-21 physical eligibility portion; RF-31; RN-22; RN-24; RN-35; RN-36 | DEC-12 | Plan/enrollment/payment model, validity, modalities, access allowance, confirmation/renewal/delinquency, and the complete pre-release eligibility decision. |
| RF-26–RF-29 | DEC-13 | Financial record meanings, statuses/calculations, periods/filters, and valid revenue/profit indicators. Nonfinancial RF-28/RF-29 indicators are not blocked by DEC-13 but still have no task. |
| RF-30 / RN-25 | DEC-14 | Class occurrence/recurrence model, visibility, capacity, reservation, and authorized exception behavior. |

Additional decision issue:

- **RN-08 — NEEDS VERIFICATION.** The original rule requires an alternative
  facial-recognition-failure flow. DEC-09 permits one additional recognition
  attempt, while DEC-11 explicitly ends this application's biometric flow and
  excludes a manual bypass. The documentation does not name a future decision
  or task that reconciles RN-08. A human decision is required before claiming
  RN-08 satisfied; this review does not invent that alternative.

DEC-01 remains unresolved but explicitly non-blocking while the original scope
is preserved. It does not excuse or block any individual missing task above.

## F. Original requirements fully covered

### Functional requirements

| Requirement | Task coverage | Completion basis |
| --- | --- | --- |
| RF-01 | Tasks 04 and 06; reverified by Task 19 | CA-01.1–CA-01.3 covered, including identity-provisioning integration. |
| RF-02 | Task 04; reverified by Task 19 | CA-02.1–CA-02.3 covered. |
| RF-04 | Tasks 02 and 06; reverified by Task 19 | CA-04.1–CA-04.3 covered for provisioned active clients. |
| RF-05 | Tasks 03 and 06; reverified by Task 19 | CA-05.1–CA-05.3 covered by UI/API role enforcement. |
| RF-09 | Task 07; reverified by Task 19 | CA-09.1–CA-09.3 covered. |
| RF-10 | Task 09; reverified by Task 19 | CA-10.1–CA-10.3 covered. |
| RF-11 | Task 10; integrated by Tasks 11–12 and reverified by Task 19 | CA-11.1–CA-11.3 covered. |
| RF-12 | Task 10; integrated by Task 11 and reverified by Task 19 | CA-12.1–CA-12.3 covered. |
| RF-13 | Task 12; reverified by Task 19 | CA-13.1–CA-13.3 covered. |
| RF-15 | Task 14 plus single-draft follow-up; reverified by Task 19 | CA-15.1–CA-15.6 covered under canonical DEC-07 policy. |
| RF-16 | Task 15; reverified by Task 19 | CA-16.1–CA-16.3 covered. |
| RF-17 | Task 13 plus Tasks 14/17 and single-draft follow-up; reverified by Task 19 | CA-17.1–CA-17.4 covered. |
| RF-18 | Task 16 plus draft-edit follow-up; reverified by Task 19 | CA-18.1–CA-18.5 covered. |
| RF-19 | Task 17; reverified by Task 19 | CA-19.1–CA-19.4 covered. |
| RF-23 | Task 22 | CA-23.1–CA-23.4 covered by the private client-linked confirmed-passage ledger. |
| RF-24 | Task 22 | CA-24.1–CA-24.4 covered by reconstructable, idempotent, non-negative occupancy. |
| RF-25 | Task 22 | CA-25.1–CA-25.3 covered by the aggregate client display and source freshness. |
| RF-32 | Task 21 | CA-32.1–CA-32.5 covered by model/unit management and lifecycle. |
| RF-33 | Task 21 | CA-33.1–CA-33.5 covered by the active public/client catalog. |

The 33 original RFs are therefore accounted for as follows:

- 19 fully covered: RF-01, RF-02, RF-04, RF-05, RF-09–RF-13, RF-15–RF-19,
  RF-23–RF-25, RF-32, and RF-33.
- 3 partially covered: RF-03, RF-06, and RF-20.
- 11 not implemented: RF-07, RF-08, RF-14, RF-21, RF-22, and RF-26–RF-31.

### Business rules

The following original rules have clear implementation/task evidence for all
currently applicable behavior: RN-01, RN-02, RN-04, RN-05, RN-11, RN-12,
RN-13, RN-14, RN-15, RN-16, RN-17, RN-19, RN-23, RN-29, RN-30, RN-31,
RN-32, and RN-33.

Their principal owners are identity/client Tasks 02–06, onboarding Tasks
09–12, training Tasks 13–17, and their Task 19 cross-module verification.
RN-32/RN-33 remain inherited constraints for every future temporal or
historical domain; future features cannot rely on this entry as evidence before
their own tests exist.

The remaining business rules are all accounted for elsewhere in this report:

- Missing with future biometric/access work: RN-06–RN-08, RN-10, RN-34.
- Deferred conditional access behavior: RN-09.
- Partial because completed workouts are absent: RN-18.
- Missing standalone domain work: RN-20, RN-21, RN-26.
- Blocked with plans/finance/classes/access: RN-22, RN-24, RN-25, RN-35,
  RN-36.
- Partial cross-domain audit rule: RN-27.
- Deferred conditional export rule: RN-28.
- Deferred auxiliary camera rule: RN-37.

### Non-functional and technology requirements

- RNF06 / CA-RNF06.1–CA-RNF06.3 is fully covered by provider-neutral
  integration boundaries and Task 19 compatible-provider/failure evidence.
- RNF01–RNF05 are not listed as fully covered because their remaining formal
  evidence is recorded in sections B/C.
- TEC-01, TEC-02, TEC-04, TEC-05, TEC-06, TEC-07, TEC-08, TEC-09, and the
  approved Python portion of TEC-03 are implemented through Task 01 and the
  feature/integration tasks. TEC-03's NestJS alternative was intentionally
  removed by DEC-03.
- TEC-10 is covered for implemented modules by pytest/Vitest unit,
  integration, and API-contract suites. Its facial-integration portion remains
  pending with RF-20–RF-22, and host-level UFW remains unowned.

### Original MVP status

All 15 original MVP RFs have implemented task coverage except the explicitly
deferred RF-03/CA-03.4 biometric criterion. Task 19's functional traceability
report records passes for the remaining MVP acceptance criteria. Formal MVP
sign-off is nevertheless incomplete because RNF01–RNF05 still have the
measurement/evidence gaps in sections B/C.

## G. Later approved extensions still pending

These are deliberately separate from missing original requirements.

| Extension | Status from available evidence | Remaining work |
| --- | --- | --- |
| EXT-RF-AI-01 | Implemented by Task 11 and reverified by Task 19. | None identified by this coverage review. |
| EXT-RF-SOC-01 | **NEEDS VERIFICATION.** Commit `de330ab` and progress backend/frontend/tests show implementation, but `docs/requirements.md` still says planned, the implementation-plan row is not marked implemented, and Task 20 has no completion marker/report. | Reconcile evidence against EXT-CA-SOC-01.1–01.6 and record authoritative completion status; this is status verification, not necessarily missing code. |
| EXT-RF-EQP-01 | Implemented with RF-32/RF-33 by Task 21. | None identified by this coverage review. |
| EXT-RF-PRES-01 | Implemented by Task 23 in the current uncommitted worktree, with its task and plan rows marked implemented there. | Preserve/commit through the normal workflow if approved; no additional product behavior is recommended here. |
| EXT-RF-LANG-01 | **PARTIAL / NEEDS VERIFICATION.** Task 18 applied the policy and Task 19 has substantial automated evidence. | Live Keycloak hosted-page confirmation and representative phone/tablet/desktop copy/formatting audit remain unverified under EXT-CA-LANG-01.4/.5. |

## H. Recommended missing tasks

These recommendations only assign documented original work; they do not add
features or resolve open decisions.

1. **Complete Task 19 RNF sign-off.** Run only the missing DEC-16 performance,
   intended-user, viewport/accessibility, soak, restart-recovery, and clean
   maintainability checks. Update status only after evidence passes.
2. **Account recovery — RF-06.** First resolve DEC-06's recovery-token portion,
   then implement CA-06.1–CA-06.3 using the existing Keycloak/SMTP boundary;
   retain the already present CA-06.4 container constraint.
3. **Employee registration and lifecycle — RF-07/RF-08/RN-03.** Define the
   minimum Employee↔Account model and authorized admin flow, then implement
   create/list/view/update/deactivate and permission removal while preserving
   history.
4. **Completed onboarding consultation — RF-14.** Add an authenticated
   own-client read-only view/API with cross-client denial; do not invent a
   post-completion edit/revision flow.
5. **Biometric enrollment — RF-22/CA-03.4/RN-10/RN-26/RN-34.** Select and
   document the actual provider for the task, implement the DEC-09 enrollment,
   quality, safe-replacement, retention/deletion, authorization, notice, and
   privacy boundaries, and satisfy CA-03.4 explicitly.
6. **Recognition and physical-access integration — RF-20/RF-21/RN-06–RN-09.**
   Implement provider-neutral recognition-result ingestion, client mapping,
   quality validation, idempotent release integration, and controlled failures.
   Stop at DEC-12 for enrollment/payment/modality/access-count eligibility and
   obtain a human decision for RN-08's alternative flow.
7. **Plan purchase/enrollment/payment validity — RF-31/RN-22/RN-24/RN-35/RN-36.**
   Resolve DEC-12 before schema/API/UI work. This task should precede claiming
   complete physical-access eligibility.
8. **Billing records and views — RF-26/RF-27.** Resolve applicable DEC-13
   financial meanings, then implement authorized recording/updating and
   own-client/staff consultation with isolation.
9. **Administrative dashboard — RF-28/RF-29.** After DEC-13, compose only the
   required existing indicators and controlled failure isolation; do not treat
   the current client-management page as the dashboard.
10. **Class schedule — RF-30/RN-25.** Resolve DEC-14, then implement occurrence
    create/change/remove and the approved corresponding view/capacity behavior.
11. **Exercise, completed-workout, and evaluation integrity — RN-18/RN-20/RN-21.**
    Create a decision/task limited to the minimum domain behavior these rules
    require. Do not infer broader exercise/evaluation CRUD beyond what a human
    approves.
12. **Critical notices and remaining audit ownership — RN-26/RN-27.** Define
    the minimum notice and tamper-resistant audit behavior for future
    permission/biometric/configuration flows, preserving the separately
    approved account-erasure exception.
13. **Auxiliary camera observations — RN-37.** Keep deferred unless prioritized;
    if scheduled, implement only DEC-10's auxiliary, zone-compatible,
    60-second-fresh observation/discrepancy behavior without changing the
    authoritative Task 22 count.
14. **Host deployment firewall — TEC-03 approved baseline.** Add a focused
    deployment task for UFW ports/rules and reproducible verification without
    redesigning the Docker Compose architecture.

No implementation of these recommendations is part of this review.
