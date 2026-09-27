# Task 28 — Shared Person and Client Registration Data

## Status

Implemented. Shared-person registration/editing, independent client activity,
identity reconciliation, and CEP success/manual fallback passed Task 37
automated and three-viewport checks. CA-03.4 remains deferred. See the
[verification report](37-instructor-role-integrated-verification-report.md).

## Objective

Replace the client's single display-name-only registration model with the
approved Account-linked personal record, expand client create/edit behavior,
and add resilient ViaCEP-assisted address entry without making registration
depend on the external service.

## Requirements covered

- RF-01: CA-01.1–CA-01.5.
- RF-03: CA-03.1–CA-03.3, CA-03.5, and CA-03.6. CA-03.4 remains deferred.
- RF-04/RF-05 only where existing client authorization and login eligibility
  must remain correct.
- EXT-RF-LANG-01 for all UI and accessible copy.

## Required reading

Read `AGENTS.md`, then this task, then only: `docs/requirements.md` sections
2.1, 2.2, RF-01, RF-03–RF-05, the approved Brazilian contact/address policy,
7.1.1, 7.3, 9.2, RN-02–RN-05, RN-23, RN-27, RN-33, RNF02–RNF04, DEC-04,
DEC-05, DEC-17, and EXT-DEC-INST-01; the current client/account, Keycloak
provisioning/reconciliation, admin client UI, and related tests; and
`docs/frontend-design.md` shared/admin form guidance.

## Exact implementation scope

- Add one Account-linked personal record owning `first_name`, multiword
  `surname`, globally unique normalized CPF, normalized Brazilian phone, CEP,
  street, number, optional complement, neighborhood, city, and two-letter UF.
  Derive presentation full name from first name plus surname; do not retain two
  independently editable name authorities.
- Validate CPF with its mathematical check digits and reject repeated-digit
  placeholders. Accept formatted CPF/phone/CEP input but persist normalized
  values. Phone represents a valid 10- or 11-digit Brazilian national number.
- Move client active state to the Client role boundary while preserving Account
  as the overall login linkage. All client-protected resolution must reject an
  inactive Client even if a later Employee role on that Account is active.
- Update authorized client creation/detail/edit APIs and AdminShell UI for every
  approved field. New clients require the complete approved data. Client has no
  CNPJ field. Search remains by name/e-mail and must use the derived full name.
- Synchronize name and e-mail changes through the existing durable Keycloak
  adapter/reconciliation boundary. Never call Keycloak from controllers or
  claim success when external/local state is inconsistent.
- Add a replaceable server-side ViaCEP adapter and an authorized lookup endpoint.
  Validate eight CEP digits before the call, use a bounded timeout, map ViaCEP
  not-found/invalid/unavailable responses to controlled pt-BR states, and never
  log full address data. Prefill only returned street, neighborhood, city, and
  UF. Number is always manual; every field remains editable; lookup failure
  never blocks saving a manually entered valid address.
- Existing data is development/test-only. A clean migration/reset is acceptable;
  do not invent name splits or placeholder CPF/address values, and do not add
  runtime code that silently deletes records.

## Boundaries

- Do not implement Employee, CNPJ, instructor routes, training behavior, or
  public CEP search.
- Do not call ViaCEP directly from the browser, add another address provider,
  cache personal addresses externally, or make lookup proof of address.
- Preserve Keycloak credential ownership and the existing secure first-access
  flow. Do not store credentials or sensitive values in logs/audit messages.

## Acceptance criteria and tests

Test CPF check digits/repeated digits, phone/CEP normalization, complete create
and all-field edit, global CPF uniqueness, search/display name, inactive-client
backend denial, name/e-mail Keycloak reconciliation and failure recovery,
ViaCEP success/partial/not-found/timeout/malformed response, manual fallback,
authorization, migration constraints, and responsive accessible admin form
states. Mock ViaCEP and Keycloak; no live service tests.

Run targeted backend/frontend tests plus `git diff --check` and
`git status --short`. Review the diff for leaked personal data, unrelated role
work, or credential handling changes.

## Completion requirements

Update only relevant requirement/task status after verification. Report files
changed, tests/results, important decisions, and unresolved issues. Do not
commit or push.

## Ready-to-run implementation prompt

Use Terra with Medium reasoning. Read `AGENTS.md`, then
`docs/tasks/28-shared-person-and-client-registration-data.md`, then only its
Required reading. Inspect the existing Account/Client, provisioning, migrations,
admin UI, and tests before editing. Implement only Task 28: shared person data,
expanded client registration/editing, role-specific client activity, Keycloak
name/e-mail reconciliation, and resilient server-side ViaCEP assistance with
always-available manual entry. Do not implement employees or instructor
features yet. Use fake external adapters in tests, run targeted backend/frontend
tests, review the full diff, and provide the required completion report. Do not
commit or push.
