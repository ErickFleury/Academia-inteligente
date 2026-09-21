# Task 06 — Client Identity Provisioning

## Objective

Integrate administrative client creation with Keycloak so every successfully
provisioned client has a client-only identity, a persisted OIDC subject link,
and a secure first-access path for defining their own password.

## Requirements covered

- RF-01: integration verification of CA-01.1–CA-01.3; Task 04 retains ownership
  of local client/account creation, validation, and uniqueness.
- RF-04: integration verification of CA-04.1–CA-04.3 for a provisioned client;
  Task 02 retains ownership of authentication.
- RF-05: integration verification of CA-05.1 and CA-05.3 with a real `client`
  role; Task 03 retains ownership of authorization policy.

## Related rules and constraints

- RN-01/RN-05: preserve independent application identity and client isolation.
- RN-02/RN-04: `account_active` controls application login, and every protected
  operation must authorize the authenticated role.
- RN-23/RN-32: credentials, action tokens, and sensitive identity details must
  not leak to logs; provisioning timestamps use the project convention.
- RNF01/RNF05: show provisioning progress and return controlled external-service
  failures without disabling unrelated application behavior.
- RNF04/RNF06: place Keycloak administration behind a focused integration
  boundary with replaceable test doubles and provider-error mapping.
- DEC-03, DEC-04, DEC-05, and DEC-17 are **blocking** for Keycloak topology,
  exact roles/provisioning, login eligibility, and account/client identifiers.

## Prerequisites

- Tasks 02–05 complete under their original scopes.
- The client identity-provisioning amendment to DEC-04 and the relevant parts of
  DEC-03, DEC-05, and DEC-17 are recorded.
- Keycloak administrative access and outbound first-access e-mail can be
  configured through non-secret environment settings. If the required-action
  delivery mechanism or compensation invariant cannot be implemented without a
  materially different decision, stop and ask.

## Required reading

Read `AGENTS.md`; RF-01 and CA-01.1–CA-01.3; RF-04 and CA-04.1–CA-04.3; RF-05
and CA-05.1/CA-05.3; RN-01, RN-02, RN-04, RN-05, RN-23, RN-32; RNF01,
RNF04–RNF06; DEC-03–DEC-05 and DEC-17; sections 4.1, 6.2, 7.1, 8.2, and 10.

## Scope

- Add a Keycloak administration adapter and configuration that can create a
  user with the normalized `account.email`, resolve its OIDC `sub`, assign
  exactly the `client` realm role, and initiate Keycloak's secure required-action
  flow for the client to define a password. Provision the Keycloak attributes
  needed by the established application authentication contract without making
  Keycloak the authority for local `account_active`.
- Configure runtime Keycloak administration through a non-browser,
  least-privilege integration identity whose secret comes from environment
  configuration. Configure reproducible local Keycloak SMTP delivery through
  the established development e-mail service; do not expose administrative
  credentials to the frontend.
- Integrate that adapter with the Task 04 administrative creation workflow.
  Success requires consistent local account/client persistence and a stored
  `account.keycloak_subject`; `account.id` and `client.id` remain
  application-generated UUIDs.
- Keep public self-registration disabled and ensure the administrative request
  cannot supply or persist a permanent or temporary password.
- Define and implement explicit orchestration for every local/Keycloak failure
  boundary. Retries must be idempotent; compensating cleanup or durable
  reconciliation must prevent silent orphan Keycloak users, duplicate users,
  or locally usable accounts without subject linkage. Do not report success
  while reconciliation is pending.
- Provide an explicit reconciliation/provisioning path for local accounts with
  a null `keycloak_subject` that predate this task; never synthesize a subject or
  assume e-mail alone proves an existing Keycloak linkage.
- Integrate authorized account e-mail updates with Keycloak so
  `account.email` and the linked Keycloak e-mail cannot silently diverge. Apply
  the same controlled failure, compensation, and retry rules to this update.
- Preserve Task 05 behavior: an inactive linked account is rejected by the
  application even if Keycloak authenticates it. Do not couple this state to
  physical gym-entry eligibility.
- Extend the administrator UI only as needed to communicate provisioning and
  first-access delivery progress or controlled failure/retry states.

## Out of scope

- Public self-registration, employee/admin provisioning, password recovery
  (RF-06), or allowing an administrator to choose a client password.
- Storing credentials, required-action tokens, or Keycloak secrets in
  PostgreSQL.
- Onboarding invitations/content (Task 07 and Tasks 09–12), biometrics, membership,
  payment, or physical-entry authorization.
- Granting `admin`, `employee`, `attendant`, or `instructor` during client
  provisioning.

## Acceptance criteria

- A valid authorized creation yields one local account/client, one corresponding
  Keycloak identity with matching normalized e-mail and only the `client` role,
  and the exact Keycloak OIDC `sub` stored in `account.keycloak_subject`.
- A later authorized e-mail change preserves the same identity linkage and
  updates both authoritative local account data and the linked Keycloak e-mail,
  or reports a controlled failure without silent divergence.
- No administrative client-creation input or PostgreSQL row contains a password
  or equivalent credential; the client receives a Keycloak first-access action
  and defines their own password while public registration remains disabled.
- After first access, an active client can authenticate and access only approved
  client behavior. UI and direct API attempts against administrative endpoints
  are denied under CA-05.1/CA-05.3.
- An inactive provisioned account remains in Keycloak/local history but is
  rejected for application login according to RN-02 and DEC-05.
- Invalid input, duplicate e-mail, Keycloak user/role/action failure, local
  persistence failure, and compensation failure each produce controlled,
  testable outcomes with no false success or silently accepted inconsistency.
- Retrying after a controlled partial failure does not create duplicate local
  accounts or Keycloak identities; pre-task null-subject accounts follow the
  explicit reconciliation path.

## Tests

Add focused backend unit tests using a fake Keycloak adapter for user creation,
exact role assignment, subject persistence, required-action initiation,
idempotent retry, and every compensation boundary. Add API/integration tests for
atomic observable outcomes, duplicate e-mail, inactive-account rejection, and
client denial of administrative APIs. Add frontend tests for provisioning,
first-access, retry, and controlled-error states as applicable. Run a local
Keycloak integration test for role, `sub`, required action, disabled public
registration, first login, and development SMTP delivery without depending on a
live external provider.

## Completion requirements

- Integration-verify the listed RF/CA without rewriting Tasks 02–05 as owners
  of this subsequently approved behavior.
- Document the selected orchestration order, compensation/reconciliation path,
  and reproducible local first-access test procedure.
- Inspect the Git diff for unrelated changes.
- Report files changed, tests executed/results, important decisions, and
  unresolved issues.
- Do not commit or push unless explicitly requested.

## Ready-to-use Terra/Medium Codex prompt

Use Terra with Medium reasoning. Read `AGENTS.md`, then
`docs/tasks/06-client-identity-provisioning.md`, then only the requirements
sections/IDs listed under Required reading. Inspect the existing repository
before modifying files. Implement only this task, preserving Tasks 02–05 as
completed prerequisites. Stop and ask if an unresolved DEC item requires a
material human decision. Run relevant backend, frontend, and local Keycloak
integration tests, review the Git diff, and provide the required completion
report. Do not commit or push.
