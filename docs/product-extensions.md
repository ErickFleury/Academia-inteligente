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

**Decision status:** `EXT-DEC-SOC-01` is approved for Task 20. New updates are
private by default; shared updates are visible to all active authenticated
clients, with no recipients, groups, followers, or guest audience. Private
updates remain author-only and are not visible to administrators merely because
of their role. Administrators can hide or restore shared updates only, with a
required reason; they cannot edit client content. Authors alone may edit or
delete their updates. Deletion immediately removes content from every view,
leaving a contentless tombstone and minimum audit metadata; hidden content is
retained so it can be restored. Active updates remain until author deletion or a
future approved account-deletion/anonymization policy. This approval adds no
reporting workflow or other social-network feature.

## EXT-RF-SOC-02 — Social client profile and post interactions

**Status:** approved post-MVP product extension; implementation planned by Task
26 under `EXT-DEC-SOC-02`.

**Description:** Replace the minimal own-profile presentation with a responsive
social profile. The profile displays the client's existing name, optional
editable nickname, optional biography, owner-managed profile picture,
follower/following information, and the client's permitted post history. A
permitted post detail displays its like count and comments. Profile visibility
is owner-controlled and defaults on for active authenticated-client viewers.

**Actors:** authenticated client profile owner; active authenticated client
viewer; authorized administrator only for the approved moderation actions.

**Acceptance criteria**

- **EXT-CA-SOC-02.1:** the owner can view and edit their optional non-unique
  nickname and biography, and only the owner can see/change the default-on
  social-profile visibility control.
- **EXT-CA-SOC-02.2:** the owner can upload, replace, and remove an approved
  profile picture; media validation, normalization, metadata removal,
  client-owned persistence, replacement cleanup, and account erasure are
  enforced.
- **EXT-CA-SOC-02.3:** only active authenticated clients can view an enabled
  other-client profile, and its response exposes only approved social fields;
  disabling visibility immediately prevents cross-client profile reads without
  changing per-post private/shared visibility.
- **EXT-CA-SOC-02.4:** unilateral follow/unfollow, unique directed follow edges,
  self-follow denial, and follower/following counts and lists follow the
  approved visibility and account-lifecycle rules.
- **EXT-CA-SOC-02.5:** profile posts are newest-first; owners receive their
  private/shared posts and moderation state, while other clients receive only
  shared, non-hidden posts and never deleted content.
- **EXT-CA-SOC-02.6:** a permitted shared post detail provides an accurate
  unique-client like count and permitted comments; like/unlike and comment
  creation/deletion enforce authenticated identity, post visibility, and
  ownership at the backend.
- **EXT-CA-SOC-02.7:** administrator hide/restore/delete moderation for shared
  comments and biography/profile-image content follows the approved reason,
  audit-minimization, no-edit, and client-visibility policy.
- **EXT-CA-SOC-02.8:** account erasure removes every social-profile record,
  image byte, follow edge, like, comment, post/tombstone, and related audit
  record; sensitive domain data is never projected into social responses.
- **EXT-CA-SOC-02.9:** EXT-DEC-PRES-01 remains independent: the presence tag is
  exposed only when its separate consent and derivation rules allow it.
- **EXT-CA-SOC-02.10:** Task 26 leaves a stable query boundary for a later feed
  but introduces no feed, recommendation, messaging, notification, ranking,
  leaderboard, block, or private-follow-request feature.

**Dependencies:** Tasks 06, 08, 20, and 23; backend-resolved client identity;
the existing account-erasure service; `EXT-DEC-SOC-01`, `EXT-DEC-SOC-02`, and
`EXT-DEC-PRES-01`.

**Privacy/security:** names and user-authored social content are visible only
through an approved social projection. E-mail, internal IDs, health, biometric,
training, payment, credential, administrative, and attendance-history data are
never included. Profile images are served through authorized application APIs,
not arbitrary user-controlled filesystem paths. See `EXT-DEC-SOC-02`.

**Approved policy:** social profile visibility defaults on but is visible only
to active authenticated clients. The optional nickname is non-unique, limited
to 40 characters, and never canonical identity. Biography is plain text and
limited to 160 characters.
Profile pictures are validated JPEG/PNG/WebP files up to 5 MiB, normalized and
stored in a dedicated PostgreSQL record. Following is unilateral; likes are
unique per client/post; comments are plain text, author-owned, and use the
existing 2,000-character post-content ceiling. Existing post
visibility/moderation, presence consent, and irreversible account erasure remain
authoritative. A future feed is explicitly deferred.

## EXT-RF-SOC-03 — Authenticated chronological social feed

**Status:** approved post-MVP product extension; implementation planned by Task
27 under `EXT-DEC-SOC-03`.

**Description:** Redesign the authenticated “Progresso” destination as a
newest-first feed of shared ProgressUpdate posts. A client composes a
private-by-default or explicitly shared text/media post, sees always-visible
like/comment counts, and opens a post to like it or participate in its
newest-first comments. Infinite loading uses a stable opaque cursor and no
ranking algorithm.

**Actors:** active authenticated client author/viewer/commenter; authorized
administrator only for approved whole-post/whole-comment moderation.

**Acceptance criteria**

- **EXT-CA-SOC-03.1:** the feed returns only permitted shared, non-deleted,
  moderation-visible posts ordered by `(created_at DESC, id DESC)` with bounded
  opaque-cursor pagination and no ranking or follow filter.
- **EXT-CA-SOC-03.2:** the top composer creates an authenticated-client-owned
  post and becomes reachable through one accessible compact side action after
  scrolling away, without duplicating drafts or controls; the same post appears
  in the author's permitted profile history.
- **EXT-CA-SOC-03.3:** posts accept up to four normalized images and comments
  one, with validated JPEG/PNG/WebP content, 5 MiB per input, bounded dimensions,
  metadata removal, authorized delivery, replacement cleanup, and erasure.
- **EXT-CA-SOC-03.4:** every feed card exposes author, time, permitted content,
  like count, and visible-comment count without hover; author name/avatar links
  use only the opaque social-profile identity.
- **EXT-CA-SOC-03.5:** post detail exposes newest-first visible comments with
  commenter username/avatar, timestamp, optional text/media, and an accessible
  composer; image-only posts and comments are valid and replies are absent.
- **EXT-CA-SOC-03.6:** only an author may edit their post/comment text and
  attachments; superseded bytes are removed and changed content displays
  “editado” based on `edited_at`.
- **EXT-CA-SOC-03.7:** a private profile may retain shared feed posts and its
  private-profile shell exposes only presentation username and permitted
  profile picture; a shared post with retained comments cannot become private,
  while likes alone do not prevent the transition.
- **EXT-CA-SOC-03.8:** administrator hide/restore/delete applies to the whole
  shared post/comment aggregate, audit data is minimized, cascades are complete,
  and account erasure leaves no identifying social media or media bytes.
- **EXT-CA-SOC-03.9:** phone, tablet, desktop, keyboard, screen-reader, loading,
  retry, end-of-feed, media-fallback, and focus-preservation states are verified.
- **EXT-CA-SOC-03.10:** the task introduces no ranking, recommendations,
  discovery/search, replies, messaging, notifications, blocks, public guest
  access, sensitive publication, camera behavior, or payment functionality.

**Dependencies:** Tasks 08, 20, 23, and 26; backend-resolved client identity;
ProgressUpdate; the social-profile policy/query boundary; irreversible account
erasure; `EXT-DEC-SOC-01` through `EXT-DEC-SOC-03`; and `EXT-DEC-PRES-01`.

**Privacy/security:** shared remains active-authenticated-client-only. Profile
privacy does not rewrite shared post visibility, but a private profile reveals
only its username presentation and permitted picture/fallback. Media follows
the parent resource's authorization. No sensitive domain data or internal
Account/Client identifier enters feed projections, media URLs, logs, or audit.

**Approved policy:** `EXT-DEC-SOC-03` resolves private-by-default publishing,
newest-first opaque cursor order, text/media validity, four/one image limits,
author text/attachment editing, “editado,” private-profile shared posts, the
comment-based private-transition guard, retained likes, newest-first comments,
whole-aggregate moderation, complete erasure, and explicit no-algorithm and
no-replies boundaries. Task 27 supersedes only the earlier feed deferral and
chronological comment presentation; it does not rewrite Tasks 20 or 26.

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

**Decision status:** `EXT-DEC-EQP-01` is approved for Task 21. The canonical
catalog grouping is `EquipmentModel`, identified by an internal UUID and
representing one logical type/model/variant. Each physical machine is an
`EquipmentUnit` belonging to exactly one model. Functional variants (for
example, Leg Press 45° and Leg Press Horizontal) are separate models.

The catalog's authoritative active quantity is derived as the count of active
units for an active model; no mutable aggregate `quantity` is authoritative.
Deactivation preserves models, units, and historical relationships. The
catalog reports total active units only, never free/currently available units.
Task 21 introduces no real-time occupancy or use semantics. Future Task 17 AI
adaptation may use an active model with active units as catalog-existence
context, not as evidence of real-time availability.

## EXT-RF-PRES-01 — Opt-in visible presence

**Status:** approved post-MVP product extension; privacy/persistence policy
resolved by `EXT-DEC-PRES-01`.

**Description:** A client may explicitly opt in to showing their current gym
presence only as a tag on their individual profile. It is not a named-presence
directory/list and is separate from anonymous occupancy in RF-24/RF-25 and
camera data in RN-37.

**Actors:** authenticated client controlling their preference; authorized viewer
of the individual client profile. No staff override or current-presence
directory is approved.

**Acceptance criteria**

- **EXT-CA-PRES-01.1:** presence visibility to other clients is off until the
  client explicitly opts in.
- **EXT-CA-PRES-01.2:** a client who has not opted in never displays a presence
  tag through their profile.
- **EXT-CA-PRES-01.3:** changing the preference affects subsequent authorized
  presence queries according to the approved timing/lifecycle rules.
- **EXT-CA-PRES-01.4:** the profile status exposes only the approved current
  presence boolean, never health, biometric, payment, credential,
  administrative, or other private data.
- **EXT-CA-PRES-01.5:** anonymous occupancy remains available independently and
  does not reveal non-opted-in identities.
- **EXT-CA-PRES-01.6:** administrative operational access does not automatically
  make a client's identity visible to other clients.

**Dependencies:** RF-23, RF-24/RF-25, Task 22, authenticated client identity,
and `EXT-DEC-PRES-01`.

**Related originals:** RF-04, RF-05, RF-23, RF-24, RF-25, RN-04, RN-05,
RN-10, RN-11, RN-23, RN-34, RN-37.

**Privacy/security:** opt-in consent and least-data presentation are mandatory.
Camera/biometric inputs must never become a client-visible identity list by
inference.

**Approved policy:** presence sharing is default-off, profile-only, derived from
private confirmed client passages (latest entry/no later exit), limited to 12
hours, and suppressed when the authoritative source is stale. Revocation is
immediate for subsequent reads. Consent never changes aggregate occupancy;
camera/biometric data cannot establish profile presence; and there is no
presence directory or staff visibility override. See `EXT-DEC-PRES-01`.

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

**2026-09-26 account-privacy amendment:** private follow requests are approved
only for a private account and are owner-accepted or rejected; they are not a
notification system. Account privacy controls all active post audiences, so a
public account's posts are authenticated-public and a private account's posts
are follower-only. The composer no longer exposes per-post visibility.

EXT-RF-SOC-02 approves the bounded follower, like, comment, and social-profile
behavior stated above; EXT-RF-SOC-03 later adds only the authenticated
chronological feed and bounded post/comment media lifecycle. No extension
approves replies, direct messaging, friend/private-follow requests, blocks,
recommendations, notifications, algorithmic rankings, leaderboards, public
guest profiles, live equipment-use tracking, or publication of sensitive data.
Those require separate product approval.
