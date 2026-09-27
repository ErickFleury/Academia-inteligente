# Task 29 — Instructor Employee Management

## Status

Implemented. Depends on Task 28. Employee editing/API feedback gaps verified
on 2026-09-27: 47 targeted backend and 7 employee UI tests pass with fake
external adapters. Task 37 subsequently passed full regression and browser
checks at all three required sizes. Intended-user usability and the availability
soak remain pending; see the
[verification report](37-instructor-role-integrated-verification-report.md).

## Objective

Implement RF-07/RF-08 for the currently approved instructor specialization,
including local Employee identity, shared-person linkage, administrative CRUD,
durable Keycloak provisioning/synchronization, secure first access, and
independent client/employee role activity.

## Requirements covered

- RF-07: CA-07.1–CA-07.6.
- RF-08: CA-08.1–CA-08.5.
- RF-04/RF-05 for employee authentication and direct API authorization.
- RF-01/CA-01.5 and RF-03/CA-03.6 integration for dual-role Accounts.
- EXT-RF-LANG-01.

## Required reading

Read `AGENTS.md`, this task, and only: `docs/requirements.md` sections 2.1,
2.2, RF-01, RF-03–RF-08, the contact/address policy, 7.1.1, 7.3, 9.2,
RN-02–RN-05, RN-11, RN-23, RN-27, RN-31, RN-33, RNF02–RNF04, DEC-04,
DEC-05, DEC-17, and EXT-DEC-INST-01; Task 28 and its implementation/tests;
the current Keycloak admin, reconciliation, first-access, e-mail, Account, and
AdminShell client-management implementations.

## Exact implementation scope

- Add Employee with an application UUID, unique Account relationship,
  independent active state, optional normalized CNPJ, and specialized role.
  The only assignable specialization is `instructor`; reject browser attempts
  to assign `admin`, `attendant`, base-only `employee`, or arbitrary roles.
- Reuse Task 28's Account-linked person fields. Do not duplicate name, CPF,
  phone, or address in Employee. Validate optional CNPJ using its mathematical
  check digits and reject repeated-digit placeholders; CNPJ is not globally
  unique.
- Authorized administrators can create, list/search, view, update every initial
  employee field, retry provisioning, and activate/deactivate employees in a
  responsive AdminShell area. User-visible and accessible copy is pt-BR.
- If normalized e-mail and CPF match one existing Client Account, attach the
  new Employee to it. If only one identifier matches or they point to different
  Accounts, reject the operation without partial writes. Support the reverse
  dual-role path completed through Task 28 client creation.
- Provision a new identity through the durable, independently retryable
  reconciliation pattern and existing secure Keycloak first-access delivery.
  Reconcile exact active roles without removing another active Client role.
  Never grant admin or attendant.
- Updating shared person data is visible consistently from both admin client
  and employee views. Reconcile Keycloak first name, surname, and e-mail while
  preserving subject linkage. Handle conflicts/partial failures explicitly.
- Deactivation immediately fails closed in backend instructor authorization,
  removes employee/instructor role mappings through reconciliation, and retains
  history. A dual-role Account remains login-enabled with `client` when its
  Client is active. Reactivation restores only approved employee roles. When no
  application role remains active, the Account overall login gate is inactive.

## Boundaries

- Do not implement attendant/admin employee creation, public registration,
  instructor feature pages, payroll, scheduling, biometrics, or a social
  profile.
- Do not duplicate Accounts for the same matching person, merge conflicting
  identities, store credentials, or trust token roles without local active
  Employee resolution.

## Acceptance criteria and tests

Test fresh employee creation/pending provisioning/secure first access, optional
CNPJ validation, admin-only CRUD, exact role assignment, retry/idempotency,
Keycloak name/e-mail sync, dual-role linking in both directions, mismatch
rejection, shared-field updates, independent activation combinations, stale
token denial, history preservation, no partial external failures, and
responsive/loading/error/empty UI states. Use fake Keycloak/e-mail adapters.

Run targeted backend/frontend tests, `git diff --check`, and
`git status --short`; inspect the full diff for privilege escalation or personal
data leakage.

## Completion requirements

Update only relevant status documentation after verification. Report changed
files, tests/results, decisions, and unresolved issues. Do not commit or push.

## Ready-to-run implementation prompt

Use Terra with Medium reasoning. Read `AGENTS.md`, then
`docs/tasks/29-instructor-employee-management.md`, then only the Required
reading. Inspect Task 28 and the current provisioning/reconciliation code before
editing. Implement only RF-07/RF-08 for instructor employees, including
dual-role Account linkage, exact role reconciliation, secure first access,
admin CRUD, and independent role activation. Do not add other employee roles or
instructor product pages. Run targeted tests with fake external adapters,
review the full diff, and provide the required completion report. Do not commit
or push.
