# Academia Inteligente — Canonical Implementation Requirements

This is the sole canonical specification for future implementation. It
preserves every requirement identifier and acceptance criterion while
integrating approved decisions and explicitly labeled product extensions.

**Coverage:** all 33 original functional requirements and 110 functional
acceptance criteria, 6 non-functional requirements and 18 non-functional
acceptance criteria, 37 business rules, 10 technology entries, 18 original DEC
questions, approved chronological decisions, and 5 approved product-extension
requirements.

**Authority:** This document is the only source of implementation requirements.
`docs/decisions.md` and `docs/product-extensions.md` retain supporting history
and detail, but do not override this specification. If they appear to conflict,
stop the affected task and request a human decision before changing this file.
`docs/implementation-plan.md` and `docs/tasks/` define execution order and
verified status, but do not create product requirements by themselves.

`docs/frontend-design.md` governs UI presentation and reuse; it does not add or
change RF/CA/RNF/RN requirements or their acceptance status.

Implementation documentation, task prompts, code identifiers, and API contracts
remain in English. The language of user-facing application UI is governed by
EXT-RF-LANG-01 in section 3.1.

Unchecked acceptance boxes preserve requirement traceability; they are not evidence
that a criterion is unimplemented or failed. Current verified status appears in
section 9.3 and is based only on completed tasks and test evidence.

## 1 Context and usage guidance

### 1.1 Product purpose and vision

Centralize and automate gym administrative, financial, and service operations,
improving establishment control and the preparation of client-specific training
plans. The system is both an administrative platform and a client-facing gym
application.

The domain includes client and employee registration, authentication and
permissions, onboarding, training plans and AI interactions, biometrics and
physical access, attendance and occupancy, charges and plans, administrative
indicators, classes, equipment, and the approved limited client-facing
extensions.

The intended client journey is:

`registration → Keycloak provisioning → secure credential setup → login → local
client resolution → personal area → onboarding → training-plan generation →
current-plan view → AI assistant → later client modules`.

Later modules may include occupancy, equipment, financial/agenda functions,
progress sharing, and opt-in visible presence according to their own scope and
decision gates. This journey expresses dependencies; it does not move every
stage into the original MVP.

### 1.2 How to interpret this document

The requirement catalog notes that some requirements may not be needed yet, may be
classified incorrectly, or may differ from what the professor requested. It
does not identify every such item. The items are therefore retained, and
conflicts are recorded in section 9. An item's presence here does not
automatically place it in the next delivery.

| Identifier | Meaning |
| --- | --- |
| RF-01 to RF-33 | Functional requirements; RF-24X and RF-25X retain their original suffix. |
| CA-XX.Y | Acceptance criterion associated with an original functional requirement. |
| RNF01 to RNF06 | Non-functional requirements with their original numbering. |
| CA-RNFXX.Y | Original non-functional acceptance criterion. |
| RN-01 to RN-37 | Business rules with their original identifiers. |
| TEC-01 to TEC-10 | Identifiers added to reference the ten technology-table entries. |
| DEC-01 through DEC-18 | Original decision questions; section 9 records which are now resolved and which remain open. |
| EXT-RF-* / EXT-CA-* | Approved additions from `docs/product-extensions.md`, never original RF/CA identifiers. |

The requirements and criteria were reorganized with spelling adjustments,
without removing conditions. Implementation notes, the suggested sequence, and
open questions are identified as guidance from this consolidation.

### 1.3 Instructions for Codex

1. Read this file before planning functionality and identify the affected RF,
   extension requirements, RNF, RN, decisions, and acceptance criteria.
2. Work within the current task's scope. Use the MVP in section 8 as a priority
   reference while respecting its dependencies and open questions.
3. Apply relevant business rules and non-functional requirements even when a
   task names only one RF.
4. Do not silently decide among technology alternatives, conditional items, or
   questions in this specification. Resolve only open items that affect the task and
   continue work independent of them.
5. Preserve identifiers so tasks, changes, and validation remain traceable to
   requirements.
6. Use acceptance checkboxes for tracking: mark an item only after its behavior
   has been implemented and verified.
7. Do not expand scope by inferring a complete feature from a diagram or a rule
   that lacks a detailed functional flow. Record the need and link it to the
   corresponding decision.
8. Follow the workflow constraints and task system in the implementation plan.
9. For client-owned protected resources, derive the local account/client from
   the authenticated Keycloak `sub`; a browser-supplied `client_id` is never
   proof of ownership.

## 2 Actors and responsibilities mentioned

| Actor or term | Responsibility indicated by the requirements |
| --- | --- |
| Client or student | Enter and view their own data, access the training plan and chat, purchase a plan, and consult information made available by the gym. |
| Attendant | Perform service activities and register a client's facial photo according to permissions. |
| Instructor, teacher, or professional | Evaluate AI suggestions, modify training plans, and create training manually; remain identifiable as responsible for plans they create or change. |
| Administrator or administrative user | Carry out authorized administrative operations. |
| Employee | Category used in registration and authorization requirements; its responsibilities must be distributed among operational roles. |
| Visitor | Consult available equipment under RF-33. |

DEC-04 resolves the current role baseline: Keycloak realm roles are `client`,
`employee`, `attendant`, `instructor`, and `admin`; attendant and instructor are
specialized employee roles. Permissions not expressly supported below remain
undefined rather than implicitly granted.

### 2.1 Authorization matrix

| Role | Approved capability boundary |
| --- | --- |
| Client | Authenticated self-service for the client's own onboarding, current training plan, AI conversation, and later explicitly approved client features. No administrative APIs. |
| Employee | Base workforce identity only; no blanket access to health, biometric, financial, or administrative data. Concrete operations require an approved specialized permission. |
| Attendant | Employee specialization; may manage biometric enrollment when RF-22 exists, but may not access health/medical onboarding data. |
| Instructor | Employee specialization; may access health information only when functionally required for approved training-plan review/work, and remains attributable under RN-31. |
| Admin | Approved administrative operations such as client management. Admin status alone does not grant unrestricted access to health or biometric data. |
| Visitor | Only public behavior explicitly approved, currently equipment consultation under RF-33 when implemented. No protected client data. |

Backend authorization is authoritative and independent from frontend route or
control visibility. Employee/admin identities are not publicly registered: the
initial administrator is realm-bootstrapped from environment configuration,
and future employees are provisioned by an authorized employee-management flow.

### 2.2 Approved authentication and identity model

- `account.id` and `client.id` are independent application-generated UUIDs.
- `account.keycloak_subject` is the unique external Keycloak OIDC `sub`; it is
  never the account or client primary key.
- `account.email` is normalized, authoritative, and globally unique even for
  inactive accounts. It is not duplicated as an authoritative client field.
- `account.account_active` alone controls application-login eligibility. It is
  separate from enrollment/payment/biometric state and physical gym access.
- `client.account_id` is a unique foreign key, establishing one Account ↔ Client
  relationship. Client-domain data belongs to Client, not Account.
- Credentials remain exclusively in Keycloak. PostgreSQL stores no password,
  temporary password, required-action token, or authentication secret.
- Administrative client creation first persists the local Account/Client pair
  and a durable, per-client provisioning record. It reports a distinct pending
  state while an independent background reconciliation provisions one Keycloak
  identity with matching e-mail and only the `client` role, persists its `sub`,
  and starts Keycloak's secure first-access required action so the client
  defines their password. A pending client cannot authenticate, and one pending
  identity never blocks another administrative registration.
- Public self-registration is disabled. Creating a client never grants an
  administrative or employee role.
- Cross-system partial failures require explicit compensation or durable,
  idempotent reconciliation. A null-subject local account is not assumed usable.
- Protected client behavior resolves `sub → account → client` server-side and
  rejects inactive, unlinked, unauthorized, or cross-client requests.

The same Account abstraction is intended for later employee/admin identities;
it is not client-specific credential storage.

## 3 Functional requirements

The 33 requirements below retain their numbering and all their
acceptance criteria. “Outside the stated MVP” means only that an item is not in
the original MVP list; it remains in the requirement catalog.

### RF-01 Register client

**Scope:** stated MVP.

Allow an administrative user to register a new client and link the client to an
e-mail address.

**Acceptance criteria**

- [ ] **CA-01.1:** with valid required fields, the system creates the client and generates a unique identifier.
- [ ] **CA-01.2:** an e-mail address already associated with another active account is rejected.
- [ ] **CA-01.3:** invalid fields return a validation message, and no partial registration is created.

### RF-02 View and search clients

**Scope:** stated MVP.

Allow administrative users to find and view registered clients.

**Acceptance criteria**

- [ ] **CA-02.1:** the administrator can list clients.
- [ ] **CA-02.2:** a search by name or e-mail returns matching records.
- [ ] **CA-02.3:** an unauthorized user cannot view third-party data.

### RF-03 Update client data and status

**Scope:** stated MVP.

Allow changes to basic registration data and client activation/deactivation.

**Acceptance criteria**

- [ ] **CA-03.1:** valid changes persist after reloading the page.
- [ ] **CA-03.2:** a deactivated client is no longer treated as an enabled user.
- [ ] **CA-03.3:** deactivation does not automatically erase the client's history.
- [ ] **CA-03.4:** enabled clients need a valid facial photo for biometrics.

**Consolidation note:** CA-03.4 depends on RF-22 biometrics, which is not in the
stated MVP. The relationship among an active client, an enabled client, a valid
photo, and payment needed definition under DEC-05; the approved result and
deferral are recorded in section 9.

### RF-04 Authenticate user

**Scope:** stated MVP.

Identify a client, employee, or administrator before allowing access to
protected areas.

**Acceptance criteria**

- [ ] **CA-04.1:** valid credentials for an active user start an authenticated session.
- [ ] **CA-04.2:** invalid credentials do not start a session.
- [ ] **CA-04.3:** protected routes without a valid session return an unauthenticated state.

### RF-05 Authorize functions by role

**Scope:** stated MVP.

Separate Client, Employee, and Administrator permissions.

**Acceptance criteria**

- [ ] **CA-05.1:** a client cannot access administrative functions.
- [ ] **CA-05.2:** an administrator can access the specified administrative operations.
- [ ] **CA-05.3:** a direct call to a forbidden API is rejected, even without using the interface.

**Consolidation note:** The requirements also mention attendants and instructors.
Their permissions need detail without assuming that all employees have the same
access; see DEC-04.

### RF-06 Recover access by e-mail

**Scope:** outside the stated MVP.

Allow recovery of an account linked to an e-mail address.

**Acceptance criteria**

- [ ] **CA-06.1:** a valid request generates a recovery message.
- [ ] **CA-06.2:** an expired or previously used token is rejected.
- [ ] **CA-06.3:** after recovery, the user can authenticate with the new mechanism/credential.
- [ ] **CA-06.4:** the SMTP server must be isolated in a Docker container.

**Consolidation note:** CA-06.4 is a technical deployment constraint for the
e-mail service, retained for traceability and also recorded in section 6.2.
DEC-03 records the SMTP versus e-mail API choice.

### RF-07 Register employee

**Scope:** outside the stated MVP.

Allow basic employee registration.

**Acceptance criteria**

- [ ] **CA-07.1:** an administrator can create an employee with the required data.
- [ ] **CA-07.2:** the employee receives a unique identifier.
- [ ] **CA-07.3:** an incompatible duplicate account/e-mail is rejected.

### RF-08 View, update, and deactivate employee

**Scope:** outside the stated MVP.

Maintain registered employees' data and status.

**Acceptance criteria**

- [ ] **CA-08.1:** an administrator can list and view employees.
- [ ] **CA-08.2:** valid changes persist.
- [ ] **CA-08.3:** a deactivated employee loses permissions linked to the account.

### RF-09 Send onboarding invitation by e-mail

**Scope:** stated MVP.

Send a registered client an e-mail containing a link for the first onboarding.

**Acceptance criteria**

- [ ] **CA-09.1:** triggering the invitation sends a message to the linked e-mail address.
- [ ] **CA-09.2:** the link points to that client's onboarding.
- [ ] **CA-09.3:** a delivery failure is recorded as a failure, not as completion.

### RF-10 Access onboarding through a secure link

**Scope:** stated MVP.

Open the form from the link received by e-mail.

**Acceptance criteria**

- [ ] **CA-10.1:** a valid token opens the corresponding form.
- [ ] **CA-10.2:** an invalid or expired token is rejected.
- [ ] **CA-10.3:** a token cannot open another client's onboarding.

### RF-11 Record physical data

**Scope:** stated MVP.

Record the physical details specified in the approved form to guide training.

**Acceptance criteria**

- [ ] **CA-11.1:** all physical fields defined in the onboarding schema can be completed and persisted.
- [ ] **CA-11.2:** fields marked as required are validated.
- [ ] **CA-11.3:** reopening the form correctly retrieves saved data while it remains editable.

**Consolidation note:** The approved schema, required fields, and their validation are not fully defined; see DEC-06.

### RF-12 Record client medications and health conditions

**Scope:** stated MVP.

Record the medical information mentioned in the meeting, including complaints, medications, and prior problems/conditions reported by the client.

**Acceptance criteria**

- [ ] **CA-12.1:** the form has identifiable areas for complaints, medications, and relevant history/problems.
- [ ] **CA-12.2:** submitted data is associated only with the correct client.
- [ ] **CA-12.3:** a user without permission cannot obtain this information through the interface or API.

### RF-13 Validate and complete onboarding

**Scope:** stated MVP.

Mark the form complete when the client finishes providing the required information.

**Acceptance criteria**

- [ ] **CA-13.1:** a form with incomplete required fields cannot be completed.
- [ ] **CA-13.2:** on completion, the system records the completion state and date/time.
- [ ] **CA-13.3:** the AI can identify that valid onboarding is available.

### RF-14 View own onboarding

**Scope:** outside the stated MVP.

Allow the client to review the data they provided.

**Acceptance criteria**

- [ ] **CA-14.1:** an authenticated client views only their own onboarding.
- [ ] **CA-14.2:** displayed values match the persisted content.
- [ ] **CA-14.3:** access to another client's onboarding is blocked.

### RF-15 Generate a training plan using AI

**Scope:** stated MVP.

Generate initial guidance/a training plan using the information provided during onboarding.

**Acceptance criteria**

- [ ] **CA-15.1:** an attempt without completed onboarding does not generate a plan.
- [ ] **CA-15.2:** with valid onboarding, a successful AI call produces a structured, persistable plan.
- [ ] **CA-15.3:** the plan is associated exclusively with the client who requested/received the generation.
- [ ] **CA-15.4:** the AI checks whether the client's health data indicates a case that is too severe; if so, no plan is created because training would be dangerous for the client.
- [ ] **CA-15.5:** the plan is created based on each client's onboarding data.

**Consolidation note:** Apply RN-12 through RN-19 and RN-29 through RN-31. The document does not define the severity criterion or the complete flow from suggestion to review to current plan; see DEC-07.

### RF-16 View current training plan

**Scope:** stated MVP.

Display the client's current plan in a format usable especially on a mobile phone.

**Acceptance criteria**

- [ ] **CA-16.1:** a client with a plan can view the current version.
- [ ] **CA-16.2:** a client without a plan receives an appropriate empty state.
- [ ] **CA-16.3:** one client cannot view another client's plan.

### RF-17 Persist and version the training plan

**Scope:** stated MVP.

Keep the generated plan and create a new version when dynamic changes take effect.

**Acceptance criteria**

- [ ] **CA-17.1:** the first generation creates the initial version.
- [ ] **CA-17.2:** an effective change creates a subsequent version and identifies it as current.
- [ ] **CA-17.3:** refreshing the page does not lose the current version.

**Consolidation note:** Versioning must also preserve previously completed workouts and identification of the responsible professional, as required by RN-18 and RN-31.

### RF-18 Converse with the AI assistant

**Scope:** stated MVP.

Provide a chat where the client can discuss their training and provide additional context.

**Acceptance criteria**

- [ ] **CA-18.1:** an authenticated client sends a message and receives a response.
- [ ] **CA-18.2:** the assistant receives context from the current plan and, when needed, that client's onboarding.
- [ ] **CA-18.3:** one client's messages do not appear in another client's conversation.
- [ ] **CA-18.4:** provider unavailability returns a controlled error and does not corrupt the training plan.

### RF-19 Dynamically adapt training through AI

**Scope:** stated MVP.

Adapt the plan when the client reports through chat that pain, a limitation, or a previous problem is interfering with training.

**Acceptance criteria**

- [ ] **CA-19.1:** in a test scenario where the client reports that a problem interferes with a particular exercise, the AI produces a context-related adaptation.
- [ ] **CA-19.2:** a change approved through the flow results in a new current version.
- [ ] **CA-19.3:** unrelated parts are not improperly removed.
- [ ] **CA-19.4:** the modified plan remains after reauthentication.

**Consolidation note:** The text requires an approved change but does not detail who approves it or the proposal states. Define this flow under DEC-07; preserve the approved plan as required by RN-16 and RN-17.

### RF-20 Receive an external turnstile-use event

**Scope:** outside the stated MVP.

Provide a REST endpoint for the external service to report a facial-identification result.

**Acceptance criteria**

- [ ] **CA-20.1:** an authenticated, valid request is accepted according to the documented JSON.
- [ ] **CA-20.2:** malformed JSON returns a validation error.
- [ ] **CA-20.3:** the integration does not require the application to implement the turnstile's operating algorithm.
- [ ] **CA-20.4:** a duplicate event with the same identifier does not create duplicate records.

**Consolidation note:** The facial result comes from an external service. The JSON contract, integration authentication, and relationship to the turnstile-release decision still need definition; see DEC-11.

### RF-21 Verify the user's identity and eligibility for access

**Scope:** outside the stated MVP.

Associate the identity reported by the facial service with the client and check whether the account is enabled.

**Acceptance criteria**

- [ ] **CA-21.1:** a known external identity is associated with the corresponding client.
- [ ] **CA-21.2:** an unknown identity produces a denial/unknown-identity decision.
- [ ] **CA-21.3:** an explicitly deactivated client is not returned as enabled.
- [ ] **CA-21.4:** the recognition response must have acceptable precision of at least 95% to be accepted.

**Consolidation note:** The 95% minimum is preserved. “Precision” may refer to model quality or match confidence; the metric and its use need clarification under DEC-09. Identification does not replace entry authorization: apply RN-06, RN-35, and RN-36.

### RF-22 Enter initial biometric data for each client

**Scope:** outside the stated MVP.

An attendant may register a valid facial photo for the client; data from that photo will be used for entry biometrics.

**Acceptance criteria**

- [ ] **CA-22.1:** the photo must pass a previously selected precision threshold.
- [ ] **CA-22.2:** if another photo is registered, it must replace the existing one, and the old photo is then discarded.
- [ ] **CA-22.3:** only employees may change the biometric-photo data associated with each client.

**Consolidation note:** Discarding the previous photo must coexist with traceability of critical changes required by RN-26 and RN-27. Define permissions, photo threshold, and retention policy under DEC-04, DEC-09, and DEC-18.

### RF-23 Record entry, exit, and attendance

**Scope:** outside the stated MVP.

Persist access events used as history/attendance.

**Acceptance criteria**

- [ ] **CA-23.1:** a valid entry event creates an entry record.
- [ ] **CA-23.2:** a valid exit event creates an exit record.
- [ ] **CA-23.3:** a repeated event is not counted twice.
- [ ] **CA-23.4:** records include related date/time and client.

### RF-24X Calculate current occupancy

**Scope:** outside the stated MVP.

Derive the number of people currently present from entry and exit events.

**Acceptance criteria**

- [ ] **CA-24.1:** a valid entry increments occupancy once.
- [ ] **CA-24.2:** a valid exit decrements occupancy once.
- [ ] **CA-24.3:** duplicate processing of the same event does not change the total again.
- [ ] **CA-24.4:** the value is not displayed as negative.

**Consolidation note:** The X suffix is retained because its meaning is not explained. RN-37 describes camera-based counting in gym spaces, whereas this RF calculates presence from entries and exits. Resolve DEC-02 and DEC-10 before choosing the behavior.

### RF-25X Display current occupancy

**Scope:** outside the stated MVP.

Show the client the number of people training at the moment.

**Acceptance criteria**

- [ ] **CA-25.1:** the page displays the value calculated by RF-24 for users.
- [ ] **CA-25.2:** after a new event is processed, a new query reflects the new total.
- [ ] **CA-25.3:** the information is legible in a mobile viewport.

**Consolidation note:** CA-25.1 references RF-24, while the corresponding requirement is labeled RF-24X. This reference is preserved and points to the previous item. See DEC-02 and DEC-10.

### RF-26 Record and update billing status

**Scope:** outside the stated MVP.

Maintain basic control of each client's monthly fees/charges.

**Acceptance criteria**

- [ ] **CA-26.1:** an authorized user records the billing period, due date, and status.
- [ ] **CA-26.2:** an update persists.
- [ ] **CA-26.3:** the record is associated with the correct client.

### RF-27 View billing status

**Scope:** outside the stated MVP.

Allow consultation of the basic financial status already recorded.

**Acceptance criteria**

- [ ] **CA-27.1:** an authorized user views the client's records.
- [ ] **CA-27.2:** the client can view their own status when that screen is part of the interface.
- [ ] **CA-27.3:** a client cannot view another person's monthly fees.

### RF-28 Provide an administrative dashboard

**Scope:** outside the stated MVP.

Present an administrative home page consolidating system information.

**Acceptance criteria**

- [ ] **CA-28.1:** only an authorized role can access the dashboard.
- [ ] **CA-28.2:** the page loads data from existing modules, such as monthly, annual, and total billing; the number of subscribing clients and employees; client access history broken down by days/hours; and possibly other indicators.
- [ ] **CA-28.3:** failure of one indicator does not grant unauthorized access or display data from another context.

**Consolidation note:** Financial indicators depend on defining the meaning of invoice, revenue, and profit; see DEC-13.

### RF-29 Display consolidated dashboard indicators

**Scope:** outside the stated MVP.

Make the dashboard useful by showing indicators from already requested functions.

**Acceptance criteria**

- [ ] **CA-29.1:** display at least the number of active clients, attendance history over the weeks, and current occupancy.
- [ ] **CA-29.2:** when the corresponding modules are implemented, a summary of total and monthly profit may be displayed.

**Consolidation note:** The occupancy indicator depends on DEC-10. Profit depends on a calculation definition and data not yet specified, as noted in DEC-13.

### RF-30 Manage the gym class schedule

**Scope:** outside the stated MVP.

Allow an administrative user to record days and times that will later be displayed.

**Acceptance criteria**

- [ ] **CA-30.1:** an administrator creates a class with at least identifying information, date, and time.
- [ ] **CA-30.2:** an occurrence can be changed or removed from the schedule.
- [ ] **CA-30.3:** changes appear in the corresponding public/authenticated view.

**Consolidation note:** The capacity rule RN-25 is conditional. Recurrence, schedule visibility, and any booking flow need definition under DEC-14.

### RF-31 Provide purchase of gym plans

**Scope:** outside the stated MVP.

Allow a user to purchase a gym plan linked to their account. The plan is valid until date X and expires after that time, requiring a new payment to become valid again.

**Acceptance criteria**

- [ ] **CA-31.1:** the client's enabled status must change only if payment was accepted with API confirmation.

**Consolidation note:** Payment confirmation must be related to the other eligibility and entry conditions without removing them. See DEC-05 and DEC-12, as well as RN-22, RN-24, RN-35, and RN-36.

### RF-32 Manage gym equipment

**Scope:** outside the stated MVP.

Allow an administrative user to register, view, update, and deactivate equipment made available by the gym, including its basic information and display image.

**Acceptance criteria**

- [ ] **CA-32.1:** an authorized administrative user can register equipment with, at minimum, a name and status;
- [ ] **CA-32.2:** the system allows an image to be associated with the equipment;
- [ ] **CA-32.3:** registered equipment remains available on a subsequent query;
- [ ] **CA-32.4:** an authorized user can change equipment information;
- [ ] **CA-32.5:** deactivated equipment no longer appears as available to the client, without requiring deletion of its record.

### RF-33 View available equipment

**Scope:** outside the stated MVP.

Allow visitors or clients to view equipment made available by the gym, together with its basic information and corresponding images.

**Acceptance criteria**

- [ ] **CA-33.1:** the interface presents the list of registered active equipment;
- [ ] **CA-33.2:** each equipment item shows at least its name and image, when an image has been registered;
- [ ] **CA-33.3:** the user can view additional equipment information when registered;
- [ ] **CA-33.4:** deactivated equipment does not appear as available;
- [ ] **CA-33.5:** the list remains usable on mobile devices.

### 3.1 Approved product-extension requirements

These approved extensions are part of this canonical specification.
`docs/product-extensions.md` retains supporting dependency, privacy, and
unresolved-decision detail.

#### EXT-RF-AI-01 — Conversational AI onboarding

**Scope:** approved MVP product extension. **Related originals:** RF-10–RF-13,
RF-15, RF-18, RN-05, RN-11, RN-23, RN-29, RN-30.

An authenticated client may start or resume a progressive AI conversation that
maps recognized answers into their authoritative structured onboarding. The AI
must leave missing/invalid information incomplete, must not diagnose, must not
bypass validation, and must preserve the secure-link/form route.

Questions may cover objectives, approved physical information, prior experience
where applicable, limitations/complaints, medications, health conditions, and
other fields only when they exist in the approved onboarding schema.

Acceptance: `EXT-CA-AI-01.1` own-client start/resume;
`EXT-CA-AI-01.2` progressive schema-based mapping and persistence;
`EXT-CA-AI-01.3` no invented values or validation bypass;
`EXT-CA-AI-01.4` resumable state; `EXT-CA-AI-01.5` RF-13 completion gates RF-15;
`EXT-CA-AI-01.6` cross-client isolation; `EXT-CA-AI-01.7` no diagnosis and
controlled provider failure; `EXT-CA-AI-01.8` coexistence with link/form.

#### EXT-RF-SOC-01 — Controlled progress sharing

**Scope:** approved post-MVP extension. **Related originals:** RF-04, RF-05,
RN-04, RN-05, RN-11, RN-23, RN-28, RN-33.

An authenticated client owns each progress update and selects private or shared
visibility. Only explicitly permitted users may view it; only its author may
modify/delete it. Sensitive account, health, biometric, financial,
authentication, administrative, or presence data is never inserted
automatically.

Acceptance: `EXT-CA-SOC-01.1` authenticated ownership;
`EXT-CA-SOC-01.2` private/shared control; `EXT-CA-SOC-01.3` enforced visibility;
`EXT-CA-SOC-01.4` author-only mutation/deletion; `EXT-CA-SOC-01.5` no automatic
sensitive content; `EXT-CA-SOC-01.6` no unapproved social-network features.

#### EXT-RF-EQP-01 — Equipment quantity by logical type/model

**Scope:** approved post-MVP extension. **Related originals:** RF-32, RF-33,
RN-04, RN-33.

Administrative equipment management and client/visitor consultation must
support the total count of active units for an approved logical type/model,
alongside name, optional image, and additional RF-33 information.

Acceptance: `EXT-CA-EQP-01.1` authorized grouping management;
`EXT-CA-EQP-01.2` active total displayed; `EXT-CA-EQP-01.3` deactivation updates
the count while preserving required history; `EXT-CA-EQP-01.4` total units are
never represented as real-time free/available units.

#### EXT-RF-PRES-01 — Opt-in visible presence

**Scope:** approved post-MVP extension, blocked by `EXT-DEC-PRES-01` and DEC-10.
**Related originals:** RF-23–RF-25X, RN-04, RN-05, RN-10, RN-11, RN-23, RN-34,
RN-37.

Named presence is a separate opt-in client feature, not anonymous occupancy and
not inferred from camera/biometric data. A non-opted-in client never appears by
name to another client, and the view exposes only minimal approved profile data.

Acceptance: `EXT-CA-PRES-01.1` default-off opt-in;
`EXT-CA-PRES-01.2` non-consenting clients excluded; `EXT-CA-PRES-01.3` preference
lifecycle enforced; `EXT-CA-PRES-01.4` sensitive data excluded;
`EXT-CA-PRES-01.5` anonymous count remains independent;
`EXT-CA-PRES-01.6` staff visibility does not imply client/public visibility.

#### EXT-RF-LANG-01 — Portuguese user-facing application

**Scope:** approved cross-cutting extension for existing, MVP, and post-MVP UI.
**Related originals:** RNF02, RNF03, RF-04, RF-10, RF-18.

Application-controlled text shown to users in public, client, and
administrative frontend areas must be in Brazilian Portuguese (`pt-BR`). This
includes navigation, actions, form labels/help, validation, loading, empty,
success, error and authorization states, dialogs, notifications, and accessible
names. In-app AI onboarding and training-chat responses must address clients in
Portuguese. Established technical or fitness terms commonly used in English,
such as “bulking,” may remain in English when that is clearer to users.
User-authored content, proper names, technical identifiers, API contracts,
implementation documentation, and Codex task prompts are not translated by
this requirement.

Acceptance: `EXT-CA-LANG-01.1` application-controlled public/client/admin UI
copy and accessible names are in `pt-BR`, including failure and empty states;
`EXT-CA-LANG-01.2` in-app AI responses and client-facing generated guidance are
in Portuguese without changing structured-data validation or safety rules;
`EXT-CA-LANG-01.3` user-facing dates, times, numbers, and currency values use
appropriate `pt-BR` formatting where displayed;
`EXT-CA-LANG-01.4` login and first-access screens displayed through Keycloak
are in Portuguese, without changing the approved authentication architecture;
`EXT-CA-LANG-01.5` representative phone, tablet, and desktop flows have no
unintended English application copy. Familiar gym/technical terms are allowed.

No extension approves followers, friends, messages, comments, likes, rankings,
leaderboards, or live equipment-use tracking.

### 3.2 Client-facing training and assistant interpretation (DEC-19)

RF-16 is implemented as a personal, mobile-usable area where the authenticated
client views only their current training-plan version, its exercises, and the
relevant instructions contained in that approved version. A browser-supplied
client ID cannot select the plan.

RF-18/RF-19 remain client-facing after onboarding. When functionally necessary
and authorized, the assistant may receive only that authenticated client's
structured onboarding, current approved plan, permitted version/history
context, and client-visible exercise/equipment information already implemented
by an approved module. Missing modules do not authorize invented context.
Suggestions and chat responses do not become the current plan: approval,
versioning, safety, professional responsibility, manual fallback, and history
rules in RF-17/RF-19 and RN-12–RN-19/RN-31 continue to govern changes.

## 4 Non-functional requirements

The six RNFs below preserve all their criteria. Measurement parameters that were not defined are collected under DEC-16.

### RNF01 Performance

The system must respond quickly to operations performed by users.

**Acceptance criteria**

- [ ] **CA-RNF01.1:** common query, navigation, and write operations must respond to the user within 2 seconds under normal usage conditions.
- [ ] **CA-RNF01.2:** operations depending on external services or inherently longer processing must indicate that processing is under way, without making the interface appear frozen.
- [ ] **CA-RNF01.3:** if an external service is unavailable or slow, the system must return a controlled error message without blocking the operation indefinitely.

### RNF02 Usability

The system must have a clean, intuitive, easy-to-use interface requiring little training.

**Acceptance criteria**

- [ ] **CA-RNF02.1:** functions intended for each role must be accessible through understandable navigation and labels, without requiring technical knowledge of the system.
- [ ] **CA-RNF02.2:** forms must clearly indicate required fields, input errors, and available actions.
- [ ] **CA-RNF02.3:** a representative user must be able to perform their role's main tasks without specific training beyond initial guidance.

### RNF03 Responsiveness

The interface must adapt to smartphones, tablets, and computers, prioritizing a good mobile experience.

**Acceptance criteria**

- [ ] **CA-RNF03.1:** main screens must remain usable on smartphones, tablets, and computers without overlapping or clipped content.
- [ ] **CA-RNF03.2:** menus, buttons, forms, and interactive elements must remain accessible and usable on small screens.
- [ ] **CA-RNF03.3:** main content must not require horizontal scrolling on smartphones at the resolutions supported by the project.

### RNF04 Maintainability

The system must be developed to require little maintenance, favoring code organization, modularity, ease of evolution, and ease of fixing problems.

**Acceptance criteria**

- [ ] **CA-RNF04.1:** changes in one module must not require widespread changes in other modules when there is no necessary functional dependency.
- [ ] **CA-RNF04.2:** system components must have well-defined responsibilities, avoiding duplicated logic and unnecessary coupling.
- [ ] **CA-RNF04.3:** significant changes must have sufficient related tests to detect regressions in affected functions.

### RNF05 Availability

The system must be available for users 24 hours a day.

**Acceptance criteria**

- [ ] **CA-RNF05.1:** core services must remain continuously available except during scheduled maintenance.
- [ ] **CA-RNF05.2:** failures of an external service, such as an AI or e-mail provider, must not make internal functions unavailable if they do not directly depend on that service.
- [ ] **CA-RNF05.3:** when an external component is unavailable, the system must report the failure in a controlled way and allow independent operations to continue.

### RNF06 Integration

External-system integrations must be decoupled so that external services can be replaced or updated without widespread system changes.

**Acceptance criteria**

- [ ] **CA-RNF06.1:** communication with each external service must use a defined interface or integration layer, avoiding direct dependencies scattered across the application domain.
- [ ] **CA-RNF06.2:** replacing a compatible external provider must require changes concentrated in its integration layer, without widespread changes to business rules.
- [ ] **CA-RNF06.3:** failures or contract changes in an external service must be handled by the integration layer and must not expose the provider's internals to other layers.

### 4.1 Cross-cutting constraints in other sections

Quality and security constraints also appear within business rules and functional criteria. They remain applicable under their original IDs; this table only helps locate them.

| Topic | References and applicable condition |
| --- | --- |
| Authentication and authorization | RF-04, RF-05, and RN-02 through RN-05: control sessions, roles, and access in the API as well. |
| Privacy and segregation | RF-12, RF-18, RN-10, RN-11, RN-23, RN-28, RN-29, and RN-34: limit access to and exposure of health data, biometrics, logs, exports, and AI context. |
| Integrity and history | RF-17, RF-20, RF-23, RF-24X, RN-01, RN-18, RN-20, and RN-33: maintain identity, history, relationships, and duplicate handling. |
| Audit and traceability | RN-03, RN-09, RN-21, RN-26, RN-27, RN-31, and RN-32: record responsible people, reasons, notices, and dates consistently. |
| Continuity during external failures | RN-08, RN-19, RNF01, RNF05, and RNF06: provide alternatives for facial recognition, manual training-plan creation, and controlled failure handling. |
| Biometric quality | CA-21.4, CA-22.1, and RN-07: observe the cited 95% minimum and the photo threshold, with metrics to be clarified under DEC-09. |
| Deployment | CA-06.4 and section 6: cover SMTP container isolation, Docker Compose, and the firewall indication. |

## 5 Business rules

All 37 business rules are preserved below, including those that also describe functions or non-functional constraints. Conditional rules retain their conditions of application.

| ID | Business rule | Indicated application |
| --- | --- | --- |
| RN-01 | Each person must have a unique identity in the system according to the identifier defined by the project. | Registration |
| RN-02 | An inactive user cannot authenticate normally. | Authentication |
| RN-03 | A deactivated employee loses operational permissions, but their history remains associated with them. | Employees/Audit |
| RN-04 | Every protected operation must consider the authenticated user's role/permission. | Security |
| RN-05 | A client may view only data belonging to their own context, except for specifically shared functions. | Privacy |
| RN-06 | Facial recognition identifies/verifies the person; entry authorization must occur in a separate step. | Biometrics/Access |
| RN-07 | A facial match below the configured threshold must never be automatically converted into a positive identification. | Biometrics |
| RN-08 | An alternative flow must exist for facial-recognition failure. | Biometrics |
| RN-09 | Every manual release that bypasses a normal access rule must record the responsible person and reason. | Access control |
| RN-10 | Biometric data must be handled separately from ordinary registration data. | LGPD |
| RN-11 | Recorded medical information, injuries, or restrictions must not be available to employees without a functional need. | LGPD |
| RN-12 | AI-generated suggestions may be viewed by instructor employees to assess their validity. | AI |
| RN-13 | AI must not create training suggestions for clients with severe health cases (such as severe heart problems). | AI/Training |
| RN-14 | The instructor must be able to modify a suggestion in full. | AI/Training |
| RN-15 | Client restrictions take precedence over optimizations suggested by AI. | AI/Training |
| RN-16 | AI must not silently modify an already approved training plan. | AI/Training |
| RN-17 | An AI-proposed change to an existing plan must result in a new proposal/version. | AI/Training |
| RN-18 | Previously completed workouts cannot be modified retroactively when the current plan is updated. | History |
| RN-19 | Failure of the AI service must not prevent the instructor from creating a training plan manually. | Functional availability |
| RN-20 | An inactive exercise may remain in historical plans but must not normally be selectable for new prescriptions. | Exercises |
| RN-21 | Evaluations must have a date and responsible person to allow chronological tracking. | Evaluation |
| RN-22 | Only active plans may give rise to new enrollments. | Plans |
| RN-23 | Sensitive information must not appear unnecessarily in technical logs. | LGPD |
| RN-24 | If the gym blocks delinquent clients, the block must be applied by the access-rules engine, not by facial recognition. | Finance/Access |
| RN-25 | If classes with participant limits are offered, confirmed reservations cannot exceed capacity without an authorized exception. | Schedule |
| RN-26 | Critical changes to permissions, biometrics, and configuration must generate a notice. | Notice |
| RN-27 | A user who performs a problematic action must not be free to erase evidence of their own action. | Audit |
| RN-28 | Exports must respect the same permissions as the screens/APIs. | Security |
| RN-29 | One client's data must never be included in AI context intended for another client. | AI/Privacy |
| RN-30 | AI responses must not be presented as medical diagnoses. | AI |
| RN-31 | The instructor/professional must remain identifiable as responsible for plans they changed/created. | Training |
| RN-32 | Every temporal record must use a consistent date/time format to preserve traceability. | System |
| RN-33 | Deletion/deactivation of an entity must not break historical relationships needed for audit. | Integrity |
| RN-34 | Biometric data must not be sent to ordinary operational reports. | LGPD |
| RN-35 | If a student does not have a valid enrollment, the system must prevent their access. Missing or expired enrollment is invalid. | Access control |
| RN-36 | The turnstile must be released only after the system validates the student's identity, the existence and validity of the enrollment, the contracted modality, and the permitted number of accesses. | Entry authorization |
| RN-37 | As auxiliary information, the gym occupancy system must show the number of people in certain gym spaces by counting people using a computer-vision model connected to surveillance cameras. | Gym occupancy |

**Classification note:** RN-37 describes a computer-vision occupancy counting and display function. RN-08, RN-09, RN-12, RN-14, RN-19, RN-21, and RN-26 also imply flows requiring detail. Their original numbering is preserved; see DEC-10, DEC-11, and DEC-15.

## 6 Technologies and technical constraints

### 6.1 Historical technology entries

The following TEC entries are preserved for traceability only. Where they list
alternatives, DEC-03's approved baseline below—not the historical alternative—is
the active implementation architecture.

| ID | Layer | Indicated technology | Recorded rationale |
| --- | --- | --- | --- |
| TEC-01 | Frontend | React + TypeScript | Componentization, strong ecosystem, and good suitability for a responsive SPA interface |
| TEC-02 | Frontend build | Vite | Simple setup for a React/TypeScript project and production build |
| TEC-03 | Backend | NestJS + Python | Modular architecture, controllers/services/guards, and good REST/OpenAPI support; add firewall; add Docker |
| TEC-04 | Database | PostgreSQL | Domain data is strongly relational and requires constraints/transactions |
| TEC-05 | Auth | Keycloak/OIDC, or secure authentication integrated into the backend for reduced scope | Avoids reinventing multiple identity mechanisms and allows standardized roles |
| TEC-06 | API | REST + JSON + OpenAPI | Suitable for the web interface and external recognition integration |
| TEC-07 | AI | Adapter for an LLM provider | Avoids coupling the domain to a single provider |
| TEC-08 | Infrastructure | Docker Compose | Makes it easier to reproduce frontend/backend/database/identity locally and on any other machine |
| TEC-09 | E-mail | SMTP or e-mail provider API | Needed for invitations and recovery |
| TEC-10 | Tests | Unit + integration + API contract | Particularly important for AI and facial integration |

### 6.1.1 Approved current technology baseline (DEC-03)

| Area | Approved implementation choice |
| --- | --- |
| Architecture/backend | Python 3.13.15 modular monolith; FastAPI 0.141.1. NestJS has no MVP responsibility and requires a future explicit decision. |
| Persistence | PostgreSQL; SQLAlchemy 2.x synchronous access; Alembic migrations; psycopg 3. |
| Frontend | React 19.3.0, TypeScript 5.9.3, Vite 8.3.0, MUI 9.0.0; Node.js 24.21.0 LTS. |
| Authentication | Keycloak 26.6.3 through OIDC; identity model in section 2.2. |
| API | REST + JSON + OpenAPI. |
| E-mail | SMTP adapter; Mailpit 1.30.7 in local Docker development. |
| AI | Provider-independent adapter; provider/model and contract remain DEC-08. |
| Runtime/deployment | Docker Compose on a Linux host; host-level UFW; PostgreSQL and other internal services are not directly Internet-exposed. |
| Tests | pytest/FastAPI `TestClient`; Vitest + React Testing Library. No Jest/Supertest for the Python backend. |
| Hosting | Undecided. |

The pinned versions above are canonical; DEC-03 retains their amendment history.
This document does not authorize upgrades.

### 6.2 Technical constraints that must also guide the work

- **Isolated SMTP:** CA-06.4 requires the SMTP server to be isolated in a Docker container. This requirement must be reconciled with the e-mail API alternative in TEC-09.
- **Backend:** TEC-03 mentions NestJS and Python together. Their responsibilities are not defined; the entry must not be interpreted as an automatic choice between the two technologies.
- **Firewall:** the backend entry calls for a firewall but does not specify product, execution location, ports, or rules.
- **Containers and execution:** TEC-03 mentions Docker, and TEC-08 indicates Docker Compose for reproducing frontend, backend, database, and identity on other machines.
- **Authentication:** TEC-05 offers Keycloak/OIDC or secure backend-integrated authentication in a reduced scope. Choose and record an approach before consolidating identity implementation.
- **API contracts:** TEC-06 indicates REST, JSON, and OpenAPI. RF-20 requires a documented JSON contract, integration authentication, validation, and duplicate-event handling.
- **Decoupled AI:** TEC-07 and RNF06 require an integration layer that avoids tying the domain to one LLM provider. The provider and model are not defined.
- **External facial service:** RF-20 assumes an external identification integration. The application need not implement the turnstile's operation algorithm, per CA-20.3; authorization rules remain the system's responsibility.
- **Camera-based counting:** RN-37 mentions a computer-vision model connected to surveillance cameras. It specifies no model, library, camera protocol, or association of that processing with Python.
- **Payments:** RF-31 requires API confirmation but does not select a payment gateway or provider.
- **Tests:** TEC-10 calls for unit, integration, and API-contract tests, with attention to AI and facial-recognition integrations.

Choices still unspecified must be handled under DEC-08–DEC-16 and extension
decision gates. Do not add providers or infrastructure as if they were approved.

## 7 Domain and architecture references

### 7.1 Data model shown in the diagrams

The domain diagrams contain different representations of the data model. They serve as references but do not form one fully reconciled schema.

| Area | Represented entities and concepts |
| --- | --- |
| Identity and administration | User, client, employee, administrator, role, permission, session, recovery, configuration, and audit. |
| Gym and offerings | Gym, plan, subscription or enrollment, charge, payment, gym class, and equipment. |
| Onboarding and health | Onboarding, physical data, complaints, medications, health conditions, and evaluations. |
| Training | Training plan, plan version, plan item, exercise, and completed workout. |
| AI | Interactions, conversation, messages, and training-change proposals. |
| Physical access | Biometrics, facial identification, turnstile, access decision, manual release, entry and exit records, and attendance. |

Recurring conceptual references include the client's link to onboarding and the plan, plan versioning, association of items with exercises, the contracting link to plan and client, and the association of access records with the client.

The diagrams vary in terminology and detail, including subscription versus enrollment and association of AI interactions with items or versions. Before creating migrations, reconcile these points with the task's RFs and RNs; see DEC-17. An entity's presence in a diagram does not by itself define a complete new interface or CRUD flow.

### 7.1.1 Implementation-oriented domain model

This is a domain inventory, not a final SQL schema. Unapproved fields and
cardinalities remain undecided.

| Entity/concept | Purpose, ownership, relationships, privacy/lifecycle |
| --- | --- |
| Account | Local identity linkage. Application UUID; unique normalized e-mail; unique nullable Keycloak subject; active state. Owns no password. Reusable by client/employee/admin identities. |
| Client | Client-domain profile with independent UUID and unique Account FK. Owns onboarding, plans, progress, and attendance relationships; deactivation preserves history. |
| Employee/role authorization | Later employee profile linked to Account; Keycloak roles and backend policy enforce specialization. Exact employee schema awaits RF-07/RF-08 work. |
| Onboarding / structured data | Client-owned draft/completed aggregate for approved physical and health fields. Structured values are authoritative; completion/timestamps follow RF-13. Health access is need-to-know. |
| AI onboarding conversation/message | Client-owned resumable EXT-RF-AI-01 interaction that maps into structured onboarding. Retention and exact message schema await DEC-08/DEC-18. |
| TrainingPlan / TrainingPlanVersion / TrainingPlanItem | Client-owned plan aggregate, immutable/versioned current/history states, responsible professional, structured exercise items. Approval states await DEC-07/DEC-15. |
| Exercise | Referenced prescription content; inactive exercises remain in history under RN-20. Full management flow awaits DEC-15. |
| AI training conversation/message/proposal | Client-scoped RF-18/RF-19 context and proposed changes. A proposal is not a current approved plan; changes use the version lifecycle. |
| Equipment / logical type-model | RF-32 administrative records and RF-33 catalog. EXT-RF-EQP-01 grouping/count model awaits EXT-DEC-EQP-01; count is not live availability. |
| ProgressUpdate | Client-author-owned social item with private/shared visibility. Audience, retention, and deletion details await EXT-DEC-SOC-01. No sensitive data is automatically derived into it. |
| Plan/Enrollment/Subscription | Client contracting and validity concepts for RF-31/RN-22/RN-35/RN-36. Cardinality, modalities, and validity await DEC-12. |
| Charge/Payment | Client financial records and external confirmation. Provider/model and financial meanings await DEC-12/DEC-13; access is restricted. |
| Biometric data | Separately protected RF-22 data; not ordinary profile data. Quality, replacement, retention, and audit await DEC-09/DEC-18. |
| AccessEvent / attendance | Idempotent client-associated entry/exit records with timestamps under RF-20/RF-23. Integration contract and exceptions await DEC-11. |
| Occupancy records | Anonymous derived/event and possible auxiliary camera counts. Source-of-truth/display behavior awaits DEC-10. |
| Presence preference/view | EXT-RF-PRES-01 opt-in state and derived named presence. Persistence and consent lifecycle await EXT-DEC-PRES-01. |
| Class/schedule | RF-30 class occurrences; recurrence, capacity, visibility, and reservations await DEC-14. |

Ownership rules apply at the backend: authenticated clients receive only their
own protected aggregates unless an explicit shared-visibility requirement says
otherwise.

### 7.2 Architecture boundaries

Historical diagrams mention ER modeling and microservices and indicate a modular backend architecture. The embedded images focus on entities and relationships; they do not establish an unambiguous division of services, their contracts, or their deployment.

Therefore, the boundary between modules and processes, allocation of responsibilities between NestJS and Python, selected authentication, and deployment design need to be recorded under DEC-03. The requirement for decoupled integrations remains valid under any chosen solution.

DEC-03 has since selected the current boundary in section 6.1.1; the paragraph
above remains historical modeling context, not an active alternative.

### 7.3 Cross-cutting authenticated API rules

- For a client-owned protected resource, the backend derives the account and
  client from the verified Keycloak subject whenever possible.
- A `client_id` in a path, query, body, local storage, or frontend state is never
  proof that the caller owns that client.
- A client accesses only their protected data unless an explicit requirement
  defines shared visibility, such as EXT-RF-SOC-01 or EXT-RF-PRES-01.
- Administrative and professional APIs enforce role and functional-need policy
  independently of frontend routes, menus, or hidden controls.
- Direct API calls receive the same denial as the UI; obscuring controls is not
  authorization.
- External adapters receive only the minimum permitted client context and map
  provider failures to controlled application errors.

## 8 MVP and implementation sequence

### 8.1 Explicitly stated MVP

The stated MVP includes the following 15 requirements:

`RF-01`, `RF-02`, `RF-03`, `RF-04`, `RF-05`, `RF-09`, `RF-10`, `RF-11`, `RF-12`, `RF-13`, `RF-15`, `RF-16`, `RF-17`, `RF-18`, and `RF-19`.

The stated critical path is:

Registration → Access → E-mail → Onboarding → AI generation → Training plan → Chat → Dynamic adaptation.

This list does not waive the RNFs and RNs associated with the selected requirements.

DEC-19 adds `EXT-RF-AI-01` to the planned MVP onboarding experience without
claiming that it existed in the original MVP list. `EXT-RF-SOC-01`,
`EXT-RF-EQP-01`, and `EXT-RF-PRES-01` are approved post-MVP extensions.

### 8.2 Dependencies requiring reconciliation

| Dependency | Implication for the MVP |
| --- | --- |
| RF-03 requires a valid photo for enabled clients, while RF-22 is not in the MVP. | Define how initial enablement occurs and when biometrics becomes necessary; DEC-05. |
| RF-09 requires e-mail infrastructure. | Define sending and failure handling before validating invitations, even if RF-06 access recovery is delivered later. |
| RF-15 and RF-19 depend on health context and change approval. | Define blocks, review, and versioning alongside RN-12 through RN-19; DEC-07. |
| RN-14 and RN-19 require full instructor editing and manual training-plan creation. | Detail how those flows fit into the AI delivery; do not consider them implemented merely because RF-15 is ready. |
| RF-04 and RF-05 presume available users and permissions. | Define initial provisioning and the permission matrix; DEC-04. |

The reproducible dependency path now is:

`client provisioning/login → secure and conversational structured onboarding →
validated completion → version lifecycle → AI generation → own current-plan
view → own-context AI chat → approved adaptation → later client modules`.

The original secure-link/form flow remains alongside conversational onboarding
until a later approved decision replaces it.

### 8.3 Suggested sequence for Codex

This order is implementation guidance added in this consolidation; it does not change MVP membership.

| Step | Work | Main references |
| --- | --- | --- |
| 1 | Reconcile decisions affecting the first delivery and prepare the necessary technical foundation. | DEC-01, DEC-03, DEC-04, DEC-05, TEC-01 through TEC-10, and RNF04/RNF06. |
| 2 | Implement authentication, authorization, client registration, and client search/view. | RF-04, RF-05, RF-01, RF-02, and RF-03. |
| 3 | Implement e-mail invitations and the onboarding form with data isolation. | RF-09, RF-10, RF-11, RF-12, and RF-13. |
| 4 | Implement the first plan, viewing, and versioning, along with necessary professional flows. | RF-15, RF-16, RF-17, and RN-12 through RN-19. |
| 5 | Implement chat and adaptation proposals while preserving approval and history. | RF-18, RF-19, RN-16 through RN-18, and RN-29 through RN-31. |
| 6 | Verify the full MVP journey and applicable non-functional criteria. | Criteria of included RFs, RNF01 through RNF06, and relevant rules. |
| 7 | Implement remaining modules in specific tasks according to project priorities. | Remaining RFs, including the decision on RF-24X/RF-25X and RN-37. |

### 8.4 Scope classification

| Major feature | Classification | Governing requirements/decisions |
| --- | --- | --- |
| Client/account CRUD, auth, authorization | Original MVP; Tasks 02–06 implemented/integration-verified | RF-01–RF-05; DEC-03–DEC-05, DEC-17 |
| Secure-link structured onboarding | Original MVP; partially implemented | RF-09–RF-13; DEC-06, DEC-18 |
| Conversational onboarding | Approved MVP extension; planned | EXT-RF-AI-01; DEC-06, DEC-08, DEC-18 |
| Portuguese user-facing UI | Approved cross-cutting extension; applies to existing, MVP, and post-MVP screens | EXT-RF-LANG-01; RNF02/RNF03 |
| Training generation/version/current view/chat/adaptation | Original MVP; planned | RF-15–RF-19; DEC-07, DEC-08, DEC-15, DEC-18 |
| Employee management, recovery, onboarding self-review | Original post-MVP; not started | RF-06–RF-08, RF-14 |
| Progress sharing | Approved post-MVP extension; planned | EXT-RF-SOC-01; EXT-DEC-SOC-01 |
| Equipment management/catalog | Original post-MVP; planned | RF-32, RF-33 |
| Equipment quantity | Approved post-MVP extension; planned | EXT-RF-EQP-01; EXT-DEC-EQP-01 |
| Access/attendance/anonymous occupancy | Original post-MVP; occupancy blocked | RF-20–RF-25X; DEC-09–DEC-11 |
| Named visible presence | Approved post-MVP extension; blocked | EXT-RF-PRES-01; DEC-10, EXT-DEC-PRES-01 |
| Billing/plans/dashboard/classes | Original post-MVP; not started | RF-26–RF-31; DEC-12–DEC-14 |
| CA-03.4 biometric readiness | Deferred, not satisfied | RF-03/CA-03.4, RF-22, DEC-05 |

## 9 Approved and unresolved decisions

This section gives the canonical status of each decision. `docs/decisions.md`
retains the chronological decision history.

| ID | Status | Canonical result or remaining question | Affected work |
| --- | --- | --- | --- |
| DEC-01 | Unresolved; non-blocking while original scope is used | Professor validation may later change scope. Preserve all original requirements and the explicit original MVP meanwhile. | Overall scope; no independent task is blocked. |
| DEC-02 | Unresolved | Meaning of the `X` suffix in RF-24X/RF-25X. Do not infer cancellation. | Occupancy tasks. |
| DEC-03 | **Resolved** | Python/FastAPI modular monolith, PostgreSQL/SQLAlchemy/Alembic, React/TS/Vite/MUI, Keycloak/OIDC, SMTP/Mailpit, Docker Compose/Linux/UFW, provider-independent AI adapters, and approved pinned baseline. NestJS has no MVP role. | All architecture and external adapters. |
| DEC-04 | **Resolved for current roles/provisioning** | Roles are client, employee, attendant, instructor, admin. Initial admin is environment-bootstrapped; clients are administratively provisioned with only client role; future employees use an administrative flow. Health/biometric access follows section 2.1. | Auth, clients, health, training, future employees. |
| DEC-05 | **Resolved** | `account_active` controls application login only; `gym_access_enabled`/physical eligibility is separate. CA-03.4 remains explicitly deferred to RF-22 and unsatisfied. | RF-03/RF-04 and future physical access. |
| DEC-06 | Partially resolved | Invitation tokens are 24-hour, client-bound, purpose-bound, hashed, single-use on intentional redemption, and superseded by resends. The onboarding schema, draft behavior, and completion prerequisites are approved; recovery-token policy remains unresolved. | Tasks 07, 09, 10, and 12 may proceed. EXT-RF-AI-01 remains gated by DEC-08 and its applicable privacy rules. |
| DEC-07 | Unresolved; blocking | Health severity criteria, proposal/review/approval states, approvers, and activation rules. | Training generation/adaptation. |
| DEC-08 | Unresolved; blocking | AI provider/model, contracts, structured outputs, context limits, retention/error behavior. | Conversational onboarding, RF-15, RF-18, RF-19. |
| DEC-09 | Unresolved | Biometric confidence/accuracy semantics, measurement, thresholds, and below-threshold behavior. | RF-21/RF-22. |
| DEC-10 | Unresolved; blocking occupancy implementation | Relationship/source of truth between access-event presence and auxiliary camera counts, spaces, freshness, and failure behavior. | RF-24X/RF-25X, RN-37, EXT-RF-PRES-01. |
| DEC-11 | Unresolved | Access-integration payload/auth/idempotency, recognition versus authorization/release, alternatives and manual override. | RF-20–RF-23. |
| DEC-12 | Unresolved | Plan/enrollment/payment model, validity/modalities/access allowance, confirmation, renewal, delinquency and purchasable plans. | RF-31, RN-22/RN-24/RN-35/RN-36. |
| DEC-13 | Unresolved | Financial meanings and calculations, periods and filters; profit is not automatically revenue. | RF-26–RF-29. |
| DEC-14 | Unresolved | Class recurrence, visibility, reservation/capacity and authorized exceptions. | RF-30/RN-25. |
| DEC-15 | Unresolved; blocking where invoked | Manual/review training, exercise maintenance, evaluations, completed workouts, critical notices, audit/export flows. | RF-15–RF-19 and related RN. |
| DEC-16 | Unresolved; blocking formal RNF sign-off | Reference load, timeouts, viewports, usability protocol and continuous-availability measurement. | Formal end-to-end RNF verification. |
| DEC-17 | **Resolved for identity/client model** | Independent Account and Client UUIDs; unique normalized Account e-mail and unique nullable Keycloak subject; one-to-one Account↔Client; no local credentials. Other domain slices remain to be decided before their migrations. | Client/identity now; later domain schemas. |
| DEC-18 | Partially resolved | Health/onboarding storage, access, logging, retention, draft replacement, and non-sensitive audit evidence are approved for Task 10. Biometric storage/replacement/retention remains unresolved. | Task 10 may proceed; AI health context and biometrics retain their relevant decision gates. |

DEC-19 is a later approved decision, not an original question: it records the
client-facing direction and four of the extension requirements in section 3.1.
EXT-RF-LANG-01 was approved separately as a cross-cutting language rule.

### 9.1 Extension decision gates

| ID | Status | Required decision | Expected task |
| --- | --- | --- | --- |
| EXT-DEC-SOC-01 | Unresolved; blocking | Shared audience semantics, moderation, deletion, and retention. | Controlled progress sharing. |
| EXT-DEC-EQP-01 | Unresolved; blocking persistence design | Canonical logical type/model and individual-unit versus aggregate inventory representation. | Equipment catalog and quantities. |
| EXT-DEC-PRES-01 | Unresolved; blocking | Consent lifecycle, visible fields, source/freshness, revocation, staff access, and retention for named presence. | Opt-in visible presence. |

### 9.2 Privacy and sensitive-data rules

| Data category | Access and handling boundary |
| --- | --- |
| Account/profile | Owner and explicitly authorized administrative operations; normalized e-mail is account-owned. Client lists remain administrative. |
| Health/onboarding | Client and only staff with functional need; attendants and admin status alone do not grant medical access. Apply RN-11/RN-23 and DEC-18. |
| Biometrics | Separate from ordinary profile data; authorized biometric staff only; never common reports or social/presence views. Apply RN-10/RN-34. |
| Authentication | Keycloak owns credentials. Tokens/secrets are not stored as domain data or logged. Subject is an external reference only. |
| Financial | Client's own allowed view and explicitly authorized operations only; never social or presence content. |
| Progress/social | Author-owned; visibility is explicit. No sensitive category is automatically copied into a post. |
| Attendance/presence | Anonymous occupancy is distinct from named opt-in presence. Identifiable events require approved operational access and privacy rules. |
| AI context | Minimum permitted context for the resolved authenticated client only. Never cross-client; no diagnosis; sensitive prompts/responses are not unnecessarily logged. |

No retention duration is invented. RN-18/RN-27/RN-33 historical and audit
preservation applies where relevant, subject to an approved sensitive-data
retention decision.

### 9.3 Current implementation status

Status is evidence-based from completed tasks and their tests, not inferred from
unchecked boxes or planned files.

| Requirement | Scope | Status | Dependency/decision | Notes |
| --- | --- | --- | --- | --- |
| Foundation | Enabler | Implemented | DEC-03 | Task 01 verified baseline. |
| RF-04 | Original MVP | Implemented | DEC-03–DEC-05 | Task 02; Task 06 integration verifies real provisioned clients. |
| RF-05 | Original MVP | Implemented | DEC-04 | Task 03; client-role denial reverified in Task 06. |
| RF-01/RF-02 | Original MVP | Implemented | DEC-04/DEC-17 | Task 04 plus Task 06 provisioning integration. |
| RF-03 | Original MVP | **Partially implemented** | DEC-05 | CA-03.1–CA-03.3 implemented; CA-03.4 deferred and not satisfied. |
| Client identity provisioning | Approved DEC integration | Implemented | DEC-03/04/05/17 | Task 06: client-only Keycloak identity, subject linkage, required action, and independent durable reconciliation. |
| RF-09 | Original MVP | Implemented | DEC-03/DEC-04/DEC-06/DEC-17 | Task 07: provisioned active client, hashed 24-hour invitation, SMTP outcome persistence, resend invalidation. |
| Frontend design system and existing UI restyle | Visual implementation enabler | Implemented | `docs/frontend-design.md` | Task 08: shared MUI theme, shells, and restyle; preserves Tasks 01–07 behavior. |
| RF-10 | Original MVP | Implemented | DEC-06 | Task 09: secure client-scoped invitation validation and intentional redemption. |
| RF-11/RF-12 | Original MVP | Implemented | DEC-06/DEC-18 | Task 10: client-scoped structured draft, physical/health validation, separate persistence, and non-sensitive audit evidence. |
| RF-13 | Original MVP | Planned | DEC-06 | Task 12; not yet implemented. |
| EXT-RF-AI-01 | Approved MVP extension | Planned | DEC-06/08/18 | Task 11; not yet implemented. |
| EXT-RF-LANG-01 | Approved cross-cutting extension | Planned verification | RNF02/RNF03 | Applies to all UI work; MVP language audit in Tasks 18–19. |
| RF-15–RF-19 | Original MVP | Planned | DEC-07/08/15/18 | Tasks 13–17. |
| MVP frontend polish | Visual implementation enabler | Planned | `docs/frontend-design.md` | Task 18, before verification. |
| MVP integrated verification | Original MVP verification | Planned | DEC-16 | Task 19. |
| EXT-RF-SOC-01 | Approved post-MVP extension | Planned | EXT-DEC-SOC-01 | Task 20. |
| RF-32/RF-33 + EXT-RF-EQP-01 | Original post-MVP + extension | Planned | EXT-DEC-EQP-01 | Task 21. |
| RF-23–RF-25X | Original post-MVP | Planned/blocked | DEC-10/DEC-11 | Task 22 implements count/view only after decisions. |
| EXT-RF-PRES-01 | Approved post-MVP extension | Blocked | DEC-10/EXT-DEC-PRES-01 | Task 23. |
| Remaining RF-06–RF-08, RF-14, RF-20–RF-22, RF-26–RF-31 | Original post-MVP | Not started | Applicable DEC items | Preserved; no implementation claim. |

## 10 Codex workflow

### 10.1 Historical task-model constraints

- Define the functionality, module, and files or folders that may be changed.
- Do not change layers, Docker, authentication, database, or frontend when outside the task's scope.
- Do not add dependencies without justification and approval.
- Create or adjust only tests related to the functionality.
- Run only tests related to the task.
- Earlier task guidance requested a completion response of at most 10 lines. Current
  `AGENTS.md` and task-file completion requirements govern the actual report
  format while preserving the same required content.

### 10.2 Traceable task template

The template below uses identifiers in this file. Replace bracketed fields for each task.

```text
Task: implement [specific functionality].

Context:
- Read AGENTS.md and docs/requirements.md.
- Use docs/requirements.md as the canonical specification; consult
  docs/decisions.md and docs/product-extensions.md only for supporting history.
- The system has [relevant modules].
- The functionality belongs to module [name].
- Functional requirements: [RF-XX].
- Non-functional requirements: [RNFXX].
- Business rules: [RN-XX].
- Recorded decisions: [DEC-XX and the corresponding decision].

Permitted scope:
- Change only [files/folders].
- Do not change [layers or modules outside the task].
- Do not add dependencies without justification and approval.

Expected behavior:
1. [Behavior tied to the requirement].
2. [Behavior tied to the requirement].

Acceptance criteria:
- [CA-XX.Y and verifiable condition].
- [CA-XX.Z and verifiable condition].

Tests:
- Create or adjust only tests related to the functionality.
- Run only the related tests.
- Record results and report what could not be verified.

Final response:
- At most 10 lines.
- Report changed files, tests run, and pending issues.
```

### 10.3 Task completion

Consider a task complete when its acceptance criteria have been verified, the relevant business rules have been followed, related test results have been recorded, and remaining limitations are explicit. Mark only criteria actually met; leave the others pending.

## 11 Terminal unresolved-decision index

Only genuinely unresolved items appear here. Their full questions, impact, and
expected tasks are in section 9 and the implementation plan. Do not resolve them
by inference.

- **DEC-01:** professor-validated final scope; non-blocking while preserving the
  original catalog/MVP.
- **DEC-02:** RF-24X/RF-25X suffix meaning; affects occupancy work.
- **DEC-06:** recovery-token policy remains unresolved. The invitation-token
  policy, structured schema, editable-draft behavior, and completion
  prerequisites are approved; conversational onboarding remains gated by its
  applicable AI/privacy decisions.
- **DEC-07:** AI health severity and review/approval lifecycle; blocks training
  generation/adaptation tasks.
- **DEC-08:** AI provider and contracts; blocks conversational onboarding and AI
  training/chat/adaptation tasks.
- **DEC-09:** biometric metrics and thresholds; blocks relevant RF-21/RF-22 work.
- **DEC-10:** occupancy source/meaning/freshness; blocks Task 22 and contributes
  to the Task 23 block.
- **DEC-11:** physical-access integration and exceptions; blocks RF-20–RF-23.
- **DEC-12:** plans, enrollment, payment, and entry eligibility details; blocks
  RF-31 and related physical-access work.
- **DEC-13:** financial indicator meanings; blocks RF-28/RF-29 financial metrics.
- **DEC-14:** class scheduling/capacity/reservation model; blocks RF-30 details.
- **DEC-15:** manual/review/exercise/audit flows; blocks the affected training
  tasks when those flows are required.
- **DEC-16:** RNF measurement protocol; blocks formal Task 19 sign-off.
- **DEC-18:** health/onboarding storage, access, logging, retention, draft
  replacement, and non-sensitive audit evidence are approved for Task 10.
  Biometric behavior and the remaining AI-sensitive-data decisions are pending.
- **EXT-DEC-SOC-01:** sharing audience and lifecycle; blocks Task 20.
- **EXT-DEC-EQP-01:** equipment grouping/inventory model; blocks Task 21's
  persistence design.
- **EXT-DEC-PRES-01:** named-presence consent/data/source/retention model; blocks
  Task 23 together with DEC-10.
