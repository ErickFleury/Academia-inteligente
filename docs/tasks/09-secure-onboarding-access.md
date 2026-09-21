# Task 09 — Secure Onboarding Access

## Objective

Validate invitation tokens and open only the onboarding associated with the intended client.

## Requirements covered

- RF-10: CA-10.1–CA-10.3.

## Related rules and constraints

- RN-05: a client may access only their own context.
- RN-23: raw tokens and health-related context must not leak into logs.
- RN-32: token expiry and use timestamps follow the shared time convention.
- RNF01–RNF03: validation feedback and the entry page remain prompt, understandable, and responsive.
- DEC-06 already resolves the 24-hour, single-use, intentional-redemption invitation policy. Its remaining schema/editability/recovery rules block only behavior this task actually needs; do not reopen the token policy.
- Task 08 and `docs/frontend-design.md` govern the onboarding entry UI.

## Prerequisites

- Tasks 07 and 08 complete; Task 06 identity provisioning is inherited through
  Task 07.
- Approved invitation-token policy in DEC-06 available; stop if an unresolved editability/recovery choice becomes material to this access flow.

## Required reading

Read `AGENTS.md`; `docs/frontend-design.md`; RF-10 and CA-10.1–CA-10.3; RN-05, RN-23, RN-32; RNF01–RNF03; DEC-06; `docs/requirements.md` sections 2.2, 4.1, 8, 9.2, and 11.

## Scope

Implement token validation and client/onboarding scoping at the backend plus the minimum frontend entry states for valid, invalid, and expired links. Apply the approved use/reuse semantics and avoid exposing whether unrelated clients exist.

Use the Task 08 ClientShell and shared states so a valid invitation transitions
visually into onboarding. Remove any temporary/developer-looking presentation
when the proper access flow is implemented; keep rejection states controlled and
clear on phone, tablet, and desktop.

## Out of scope

- Physical or health form fields (Task 10), conversational onboarding (Task 11),
  and completion (Task 12).
- General authentication/password recovery.
- Inventing token lifetimes or post-completion edit behavior.

## Acceptance criteria

- CA-10.1: a valid token opens the corresponding onboarding entry state.
- CA-10.2: invalid and expired tokens are rejected with a controlled response.
- CA-10.3: a token cannot retrieve or mutate another client's onboarding.

## Tests

Add token validation unit tests and API/UI integration cases for valid, malformed, expired, reused (as defined), and cross-client attempts. Avoid real e-mail services. Run the relevant tests and report results.

## Completion requirements

- Verify every assigned CA.
- Inspect the Git diff for unrelated changes.
- Report files changed, tests executed/results, important decisions, and unresolved issues.
- Do not commit or push unless explicitly requested.

## Ready-to-use Terra/Medium Codex prompt

Use Terra with Medium reasoning. Read `AGENTS.md`, then `docs/tasks/09-secure-onboarding-access.md`, then only the requirements sections/IDs listed under Required reading. Inspect the existing repository before modifying files. Implement only this task, preserving the separate authenticated client identity and token-bound entry paths. Follow `docs/frontend-design.md` and reuse Task 08 shared layout/components; do not introduce an independent visual language. Check phone, tablet, and desktop. Stop and ask if an unresolved DEC item requires a material human decision. Run relevant tests, review the Git diff, and provide the completion report required by `AGENTS.md` and this task. Do not commit or push.
