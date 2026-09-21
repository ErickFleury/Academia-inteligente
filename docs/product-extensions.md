# Approved Product Extensions

## Purpose and authority

This document retains the approval history and detail for product extensions.
The sole canonical implementation specification is `docs/requirements.md`,
which includes these extensions. Original RF, CA, RNF, RN, TEC, and DEC
identifiers remain unchanged.

Extension IDs use `EXT-RF-<AREA>-NN`; their acceptance criteria use
`EXT-CA-<AREA>-NN.N`. An extension does not become part of the original MVP
merely because it is approved.

## EXT-RF-AI-01 — Conversational AI onboarding

**Status:** approved product extension; implemented in Task 11 for the MVP onboarding journey.

**Description:** After authenticating, a client may complete or resume
onboarding through a progressive AI conversation. The conversation is an
orchestration and user-experience layer over the approved structured onboarding
schema; it does not replace that schema, server-side validation, or the existing
secure-link/form path.

Questions may cover training objectives, approved physical fields, prior
experience where present in the schema, limitations/complaints, medications,
health conditions, and other explicitly approved onboarding fields. This list
does not itself approve a missing field or a medical inference.

**Actors:** authenticated client; authorized instructor/professional only where
the original requirements permit access to the resulting health/training data.

**Acceptance criteria**

- **EXT-CA-AI-01.1:** an authenticated client can start or resume only their own
  onboarding conversation.
- **EXT-CA-AI-01.2:** questions are asked progressively from the approved
  onboarding schema, and recognized answers are mapped to and persisted in the
  authenticated client's structured onboarding fields.
- **EXT-CA-AI-01.3:** absent, ambiguous, or invalid required information remains
  incomplete and is identified to the client; the AI does not invent values or
  bypass field validation.
- **EXT-CA-AI-01.4:** a client can leave and later resume with previously saved
  structured answers and approved conversation state intact.
- **EXT-CA-AI-01.5:** onboarding is concluded only when the authoritative
  structured data satisfies RF-13; the result is then available to RF-15.
- **EXT-CA-AI-01.6:** conversation, structured answers, and AI context from one
  client are never exposed to another client.
- **EXT-CA-AI-01.7:** responses do not present medical diagnoses, and AI/provider
  failure leaves already persisted structured data consistent and recoverable.
- **EXT-CA-AI-01.8:** the RF-09/RF-10 link and structured form remain usable
  unless a later approved decision deliberately replaces them.

**Dependencies:** RF-04, RF-05, RF-09–RF-13, Task 06 identity linkage, the
approved structured onboarding schema, provider-independent AI integration,
DEC-06, DEC-08, and DEC-18.

**Related originals:** RF-10–RF-13, RF-15, RF-18, RN-05, RN-11, RN-23,
RN-29, RN-30, RNF01, RNF03, RNF05, RNF06.

**Privacy/security:** backend identity-to-client resolution is mandatory. Only
the minimum permitted client context may be sent to the AI adapter; health data
and conversation text are sensitive and must not leak through logs or other
clients' contexts.

**Decision status:** Task 11 uses the approved DEC-06 schema, a provider-neutral
adapter boundary from DEC-08 (OpenAI initially; Ollama also approved for local
development/test), and client-only five-day raw-message retention from DEC-18.
This does not resolve contracts for later AI features, biometric policy, or
RF-13 completion.

## EXT-RF-SOC-01 — Controlled progress sharing

**Status:** approved post-MVP product extension.

**Description:** Authenticated clients may create a minimal progress update and
choose whether it remains private or is shared with the approved audience. This
is limited progress sharing, not a general-purpose social network.

**Actors:** authenticated client author; authenticated client viewer where the
visibility policy permits; authorized administrator only if a later moderation
or support rule explicitly grants access.

**Acceptance criteria**

- **EXT-CA-SOC-01.1:** an authenticated client can create a progress update
  owned by their resolved local client identity.
- **EXT-CA-SOC-01.2:** the author can select private or shared visibility, and a
  private update is visible only to its author unless a separately approved
  operational rule applies.
- **EXT-CA-SOC-01.3:** an authenticated user sees only updates whose visibility
  policy explicitly includes that user.
- **EXT-CA-SOC-01.4:** a user cannot modify or delete another author's update by
  interface or direct API request.
- **EXT-CA-SOC-01.5:** onboarding/health data, biometrics, payment data,
  credentials, administrative data, and attendance/presence details are never
  inserted into a post automatically.
- **EXT-CA-SOC-01.6:** the feature introduces no followers, friend requests,
  direct messages, comments, likes, rankings, or leaderboards.

**Dependencies:** Task 06 client identity provisioning, backend ownership
authorization, and an approved visibility/audience model.

**Related originals:** RF-04, RF-05, RN-04, RN-05, RN-11, RN-23, RN-28,
RN-33, RNF02–RNF04.

**Privacy/security:** sharing is explicit; private and sensitive data are not
derived into social content. Backend checks authorship and visibility without
trusting a browser-provided client ID.

**Unresolved decisions:** `EXT-DEC-SOC-01` must define whether “shared” means all
authenticated clients or explicit recipients/groups, plus any moderation,
deletion, and retention rules. The progress-sharing implementation task must
stop before persistence/API design if this remains unresolved.

## EXT-RF-EQP-01 — Equipment quantities by logical type/model

**Status:** approved post-MVP product extension.

**Description:** In addition to RF-32/RF-33 equipment management and
consultation, users can understand the total number of active units belonging
to the same approved logical equipment type/model.

**Actors:** authorized administrative user; client; visitor where RF-33 permits
public consultation.

**Acceptance criteria**

- **EXT-CA-EQP-01.1:** an authorized administrator can manage the information
  needed to associate equipment units or inventory records with an approved
  logical type/model.
- **EXT-CA-EQP-01.2:** the client/visitor catalog displays the total active
  quantity for each logical type/model together with its name and optional
  image/additional information from RF-33.
- **EXT-CA-EQP-01.3:** deactivating a unit or inventory record updates the next
  quantity query without deleting historical records required by RN-33.
- **EXT-CA-EQP-01.4:** the interface and API label the value as total active
  units and do not represent it as real-time free/available equipment.

**Dependencies:** RF-32, RF-33, an approved equipment grouping model, and the
existing administrative authorization baseline.

**Related originals:** RF-32, RF-33, RN-04, RN-33, RNF01–RNF04.

**Privacy/security:** equipment catalog data is non-client-specific; management
operations remain administrative and backend-authorized.

**Unresolved decisions:** `EXT-DEC-EQP-01` must define the canonical grouping
and whether persistence represents individual units, aggregate inventory, or
both. It must not introduce live occupancy/use semantics.

## EXT-RF-PRES-01 — Opt-in visible presence

**Status:** approved post-MVP product extension; blocked pending privacy and
persistence decisions.

**Description:** A client may eventually opt in to having their current gym
presence shown by name/profile to other authenticated clients. Named presence
is separate from the anonymous occupancy count in RF-24X/RF-25X and from camera
data in RN-37.

**Actors:** authenticated client controlling their preference; authenticated
client viewing opted-in people; administrators only under separately approved
operational permissions.

**Acceptance criteria**

- **EXT-CA-PRES-01.1:** presence visibility to other clients is off until the
  client explicitly opts in.
- **EXT-CA-PRES-01.2:** a client who has not opted in never appears by name or
  profile in another client's presence view.
- **EXT-CA-PRES-01.3:** changing the preference affects subsequent authorized
  presence queries according to the approved timing/lifecycle rules.
- **EXT-CA-PRES-01.4:** the named list includes only the minimal approved profile
  information and never health, biometric, payment, credential, administrative,
  or other private data.
- **EXT-CA-PRES-01.5:** anonymous occupancy remains available independently and
  does not reveal non-opted-in identities.
- **EXT-CA-PRES-01.6:** administrative operational access does not automatically
  make a client's identity visible to other clients.

**Dependencies:** RF-23, RF-24X/RF-25X, DEC-10, authenticated client identity,
and an approved named-presence privacy/persistence model.

**Related originals:** RF-04, RF-05, RF-23, RF-24X, RF-25X, RN-04, RN-05,
RN-10, RN-11, RN-23, RN-34, RN-37.

**Privacy/security:** opt-in consent and least-data presentation are mandatory.
Camera/biometric inputs must never become a client-visible identity list by
inference.

**Unresolved decisions:** `EXT-DEC-PRES-01` must define consent lifecycle,
visible profile fields, source and freshness of “currently present,” revocation,
staff access, and retention. DEC-10 remains separately unresolved for occupancy
source-of-truth behavior. Implementation must stop until both relevant decisions
are approved.

## EXT-RF-LANG-01 — Portuguese user-facing application

**Status:** approved cross-cutting extension for existing, MVP, and post-MVP UI.

**Description:** Application-controlled text visible in public, client, and
administrative frontend areas must be in Brazilian Portuguese (`pt-BR`).
Documentation, Codex prompts, code identifiers, and API contracts remain in
English. Established gym or technical terms commonly used in English, such as
“bulking,” may remain when clearer to users. This does not require translating
user-authored content or proper names.

**Actors:** visitors, clients, employees, attendants, instructors, and admins
using application UI; clients using in-app AI conversations.

**Acceptance criteria**

- **EXT-CA-LANG-01.1:** application-controlled public, client, and admin UI
  copy and accessible names are in `pt-BR`, including loading, empty,
  validation, error, success, and authorization states.
- **EXT-CA-LANG-01.2:** in-app AI responses and client-facing generated
  guidance are in Portuguese without bypassing structured-data validation or
  safety rules.
- **EXT-CA-LANG-01.3:** displayed dates, times, numbers, and currency values
  use appropriate `pt-BR` formatting.
- **EXT-CA-LANG-01.4:** Keycloak-hosted login and first-access screens shown
  to users are in Portuguese without changing the approved auth architecture.
- **EXT-CA-LANG-01.5:** representative phone, tablet, and desktop flows have
  no unintended English application copy; familiar gym/technical terms may
  remain in English.

**Dependencies:** the shared frontend design system, existing UI flows, and
the Keycloak identity integration for hosted credential screens. Future UI
tasks inherit this rule; Tasks 18–19 audit and verify MVP coverage.

**Related originals:** RF-04, RF-10, RF-18, RNF02, RNF03.

**Privacy/security:** language changes must not expose provider internals,
authentication details, or another client's data in error or AI responses.

**Unresolved decisions:** none for the language policy. Any provider-specific
Keycloak UI change remains a separate scoped integration step if configuration
alone is insufficient.

## Explicit exclusions

No extension in this file approves direct messaging, followers, friend
requests, comments, likes, rankings, leaderboards, live equipment-use tracking,
or publication of sensitive data. Those require separate product approval.
