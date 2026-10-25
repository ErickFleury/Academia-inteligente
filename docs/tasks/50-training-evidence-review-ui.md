# Task 50 — Evidence Review and Training Abstention UX

**Current owner-RAG scope — 2026-10-25:** client/instructor views and source notices
are implemented and tested, with synchronous credential isolation. Professional
judgments/custody are optional tools rather than RAG enablement gates. Manual
browser/keyboard/viewport QA remains unexecuted because this session exposes no
browser surface. See [current delivery](46-59-owner-rag-delivery.md).

**Status:** authenticated production-view wiring and automated development checks
implemented (2026-10-24); browser/keyboard/responsive and intended-user checks,
professional acceptance and release remain incomplete.
**Feature task:** EVID-IMPL-06.

See the [integrated status report](51-training-prescription-verification-report.md).
The [approved development exception](../training-prescription-development-amendment.md)
permits the [isolated UI/preview](48-50-isolated-prescription-development-report.md).
The later [operational follow-up](45-51-operational-integration-follow-up.md)
connects client/instructor production views to the authenticated backend. This
wiring does not enable an approved cohort or waive the disabled deployment gate.

## Objective

Owner scope update (2026-10-24): EXT-CA-AI-02.23–25 explicitly add an instructor
review/custody destination at `/instrutor/evidencias`, using the existing shell.
It supports attributable judgments and protected synthetic evaluation custody,
including review of public frozen protocols. It does not add general corpus
administration or release policies automatically. See the
[instructor workflow](../training-evidence-instructor-workflow.md).

Explain when generation was discarded and let instructors inspect the evidence
and reviewed rules behind an accepted proposal without implying proven efficacy.

## Requirements covered

- EXT-RF-AI-02: EXT-CA-AI-02.11/13/16–17/20; .8/10/21–22 UI integration.
- RF-15/CA-15.8–10, RF-16, RF-18/CA-18.4/6–8 and RF-19 review integration.
- EXT-RF-INST-02/03 and EXT-RF-LANG-01, existing display/authoring boundaries.

## Related rules and constraints

RN-04/05, RN-11–RN-19, RN-23, RN-29–RN-33; RNF01–06; DEC-07/08/15/18,
EXT-DEC-AI-02. Backend authorization/gating remains authoritative. All visible
and accessible application copy is pt-BR. Reuse the existing MUI design system.

## Prerequisites and required reading

Task 49 outcome/trace contracts exist. Read `AGENTS.md`,
`docs/frontend-design.md`, feature overview, EXT-RF-AI-02 and listed canonical
RF/CA/extensions/rules/RNF/decisions, including privacy section 9.2. Inspect the
client chat/current-plan previews, source display, instructor pending/detail/edit
views, shared components, API client and related frontend tests before editing.
Read [the methodological protocol](../training-evidence-methodology.md), section
5. Distinguish the four outcome categories in visible and accessible feedback;
only a documented restriction conflict can describe an identified prescription
conflict. Missing evidence/input or a technical failure is not proof of harm.
Read [the execution contracts](../training-prescription-execution-contracts.md),
sections 2–3 and 5–7, for typed projections, input confirmation and manual assumption.

## Permitted scope and expected behavior

1. Use existing loading/error/feedback patterns during generation. On abstention,
   explain that a new proposal could not be generated with adequate support,
   state the useful reason, and direct the client to existing instructor/manual
   review options. Do not create an unauthorized messaging or notification system.
2. Example copy: “Não foi possível gerar uma proposta com evidências suficientes
   para este pedido. Peça ao instrutor uma avaliação e a elaboração do treino.”
   Adapt the reason without leaking raw health data, prompts or provider internals.
3. Show no rejected workout or submission action. If an older saved draft remains,
   label it clearly so it cannot be mistaken for the unsuccessful replacement.
4. On accepted proposals, preserve day tables, goal, review-required status and
   sources. Present prescription eligibility separately from bibliographic status;
   use modest language such as “Critérios verificados para esta proposta”.
5. In existing instructor detail/review, expose material decision → policy rule →
   source locator, supported scope, limitations and review/version information.
   Keep raw client chat private and administrative roles outside medical access.
6. Indicate when a draft is legacy, edited or awaiting revalidation. Backend
   rejection of stale submission/approval must produce reload/revalidation
   feedback. Manual instructor edits clear AI qualification visibly while keeping
   the existing author/edit/approve workflow; do not offer an AI-gate override.
7. Avoid technical implementation labels or unsupported claims of safety,
   clinical validation, superiority or universal personalization. Evidence details
   should help a professional review an actual prescription decision.
8. Present focused input questions and the effective facts that need confirmation
   before generation, using the existing authenticated chat/form patterns. Respect
   source authority and conflicting health reports; an explicit unambiguous request
   may supply confirmation without another redundant question. Never silently edit
   onboarding. Changes invalidate dependent qualification and require revalidation.
9. Render exercise/dose/load/progression values from the backend's validated typed
   projection; do not display alternate writer prose as a competing prescription.
   Show session scope accurately and do not imply weekly validation for a sheet.
10. In the existing instructor edit/review surface, add the explicit manual-assumption
    action for an already saved accessible draft. Require exact revision and reason,
    explain the loss of AI qualification and preserved lineage/responsibility, then
    retain the normal save/approve workflow. Client roles and discarded candidates
    never receive this action. Show affected-source/policy qualification status
    through existing authorized surfaces without a new notification service.

Permitted areas: existing frontend training/chat/instructor views and shared
components only where needed, the explicitly authorized instructor evidence
review/custody workspace, API types/projections and focused tests. No general
corpus administration, source uploader, auth flow or broad redesign.

## Acceptance criteria

- EXT-CA-AI-02.11: understandable pt-BR states distinguish abstention, older
  saved content and accepted unapproved proposals; rejected content has no action.
- Instructors can follow decision-level rule/source evidence without private chat;
  clients cannot access other clients' data or privileged review details.
- EXT-CA-AI-02.13: edits/staleness remove current AI qualification; backend remains
  authoritative even for direct requests or stale browser state.
- Existing mobile/tablet/desktop behavior, keyboard access and screen-reader
  feedback remain usable; long source/trace content does not overflow layouts.
- EXT-CA-AI-02.16–17/20: displayed prescription values equal typed projections;
  confirmed inputs preserve authority and change invalidation; manual assumption
  is instructor-only, revision checked and unavailable for discarded candidates.

## Tests and validation

Add focused Vitest/React Testing Library cases for outcome reasons, no rejected
table/action, preserved older draft, trace presentation, edited/stale state,
loading/retry, reason-category correctness and accessible pt-BR feedback. Include
an outage and a coverage gap that must not imply the client cannot exercise.
Test input clarification/confirmation/conflicts, typed-to-display equality,
session-versus-week scope, edited/expired/legacy states, manual assumption with
and without content edits, preserved AI lineage and client-role denial.
Run affected tests, `npm run lint`
and `npm run build` in `frontend`. Verify existing supported phone/tablet/desktop
viewports and keyboard behavior; report manual checks separately. Run backend
projection/privacy tests only when those projections change. Review Git diff.

## Completion requirements

Report files, tests/build, viewport/accessibility evidence, copy decisions and
unresolved checks. No claim of professional or clinical validation; no commit/push.

## Ready-to-use Codex prompt

Read `AGENTS.md`, this task, Required reading and frontend design rules. Integrate
the backend abstention and trace contracts into existing client/instructor views
using shared MUI components and pt-BR copy. Preserve private-chat boundaries and
manual review. Run targeted tests/build and responsive/accessibility checks,
review the diff, and report files, checks, decisions and gaps in at most 10 lines.
Do not commit or push.
