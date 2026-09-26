# Task 26 — Social Client Profile and Post Interactions

## Objective

Redesign the authenticated “Meu perfil” area as the bounded social profile
approved by EXT-RF-SOC-02. Add owner-managed profile identity presentation,
profile-picture lifecycle, default-on authenticated visibility, following,
profile post history, post-detail likes/comments, administrator moderation, and
complete account-erasure coverage while preserving the independent Task 20 post
visibility and Task 23 presence-consent rules.

This task prepares stable social-profile and post-interaction query boundaries
for a separately approved future feed. It does not implement that feed.

## Requirements covered

- EXT-RF-SOC-02: EXT-CA-SOC-02.1–EXT-CA-SOC-02.10.
- EXT-RF-SOC-01 only as the implemented ProgressUpdate ownership,
  private/shared visibility, moderation, tombstone, and erasure behavior being
  integrated into profiles and post detail.
- EXT-RF-PRES-01 only as the implemented independent presence tag being retained
  on an individual profile when EXT-DEC-PRES-01 permits it.
- EXT-RF-LANG-01 for all new user-visible and accessible text.

## Related rules and approved decisions

- RN-04/RN-05: resolve caller identity server-side and enforce every owner,
  viewer, follower, interaction, and administrator action at the backend.
- RN-11/RN-23/RN-28/RN-33: sensitive data, logs, social projection, audit
  minimization, historical state, and erasure boundaries remain protected.
- EXT-DEC-SOC-01 remains authoritative for each post's private/shared state,
  author mutation, administrator post moderation, and contentless tombstone.
- EXT-DEC-SOC-02 is resolved for the complete Task 26 profile/image/follow/
  like/comment/moderation/erasure scope.
- EXT-DEC-PRES-01 remains authoritative and independent. Default-on social
  profile visibility never opts the client into identifiable presence.
- DEC-17 identity rules remain unchanged: Account and Client identities are
  independent and Keycloak continues to own credentials.

## Prerequisites and dependencies

- Tasks 06, 08, 20, and 23 are implemented.
- Inspect the current Client, progress, presence, administrator moderation, and
  account-erasure implementations and tests before editing.
- Reuse the existing React Router SPA navigation, ClientShell/AdminShell, shared
  UI primitives, authorization dependencies, transaction patterns, and Alembic
  conventions.

## Required reading

Read `AGENTS.md`, then this task, then only the following canonical material:

- `docs/requirements.md`: EXT-RF-SOC-01, EXT-RF-SOC-02,
  EXT-RF-PRES-01, EXT-RF-LANG-01, RF-03–RF-05, RN-04, RN-05, RN-11,
  RN-23, RN-28, RN-33, RNF02–RNF04, sections 7.1.1, 7.3, 9.1, and 9.2;
- `docs/decisions.md`: EXT-DEC-SOC-01, EXT-DEC-SOC-02,
  EXT-DEC-PRES-01, and DEC-17;
- `docs/product-extensions.md`: EXT-RF-SOC-01, EXT-RF-SOC-02, and
  EXT-RF-PRES-01;
- `docs/frontend-design.md`: shared foundations, ClientShell/AdminShell,
  progress-sharing language, and Social profile guidance;
- Tasks 20 and 23 plus their current implementation/tests;
- the current client-erasure implementation and exhaustive erasure tests.

## Exact implementation scope

### Social profile and identity presentation

- Replace the current presence-preference-only “Meu perfil” page with the
  responsive social profile while retaining the Task 23 presence preference
  and derived tag as a distinct section.
- Persist one client-owned social profile with a stable opaque UUID resource
  identifier. Never use name or nickname as canonical identity or route lookup,
  and never expose Account or Client UUIDs through the social projection.
- Display the existing client name. Allow only the owner to set/remove a
  trimmed, plain-text, non-unique nickname of at most 40 characters and a
  trimmed, plain-text biography of at most 160 characters.
- Social profile visibility defaults to enabled for existing and new clients.
  Only the owner sees or changes the visibility switch. The owner always reads
  their profile. An active authenticated other client may read it only while it
  is enabled. Anonymous users, inactive clients, instructors, attendants,
  employees, and administrators receive no client-view override merely because
  of their role.
- Disabling the profile immediately blocks subsequent cross-client profile,
  profile-post-collection, and follower/following reads. It retains follow
  edges and does not alter ProgressUpdate visibility or the Task 23 presence
  preference.

### Profile-picture lifecycle

- Make the profile picture an accessible owner-only upload/change control. A
  keyboard user must be able to invoke it; another viewer sees a non-editable
  image or fallback avatar.
- Accept only JPEG, PNG, or WebP input up to 5 MiB. Validate decoded image
  content rather than trusting filename/Content-Type, reject malformed or
  animated/unsupported content, normalize orientation and dimensions to a
  bounded maximum of 1024×1024, remove metadata, and re-encode safely.
- Store normalized bytes, media type, dimensions, and lifecycle timestamps in a
  dedicated PostgreSQL record with a unique client relationship. Do not store
  base64 in ordinary JSON, external URLs, host filesystem paths, or image bytes
  in Client/Account columns.
- A narrowly scoped maintained Python image-decoding dependency such as Pillow
  is permitted if the backend has no safe decoder. Do not introduce object
  storage, a media service, CDN, or another framework.
- Serve image content through an authorized endpoint. The frontend may fetch it
  as a blob and manage/revoke an object URL; do not expose credentials in an
  image URL. Replacement/removal deletes prior bytes in the same transaction.

### Cross-client profile access and following

- Add a read-only other-client profile route based on the opaque social-profile
  UUID. Existing shared progress cards may link the author to that route only
  when the profile is currently visible to the viewer; this is discovery from
  the existing Task 20 surface, not a new feed.
- A visible profile exposes only name, optional nickname, visible biography,
  visible profile picture, follower/following counts and lists, permitted
  newest-first posts, follow state, and the Task 23 presence tag when separately
  allowed.
- Implement unilateral follow/unfollow. Enforce a unique directed
  follower/followed pair, deny self-follow, require both clients to be active,
  and require the target profile to be visible at action time. Make retries
  converge without duplicate edges.
- Visible follower/following lists contain minimized social profile summaries
  and no e-mail, internal Client/Account ID, or sensitive fields. A hidden
  profile's graph remains persisted but unavailable to other clients.

### Profile posts and post detail

- Reuse ProgressUpdate as the only post aggregate. Do not copy post content into
  a profile table or introduce a second post model.
- List profile posts newest-first. The owner sees non-deleted private/shared
  posts and moderation state/reason. Another client sees only shared,
  non-deleted, moderation-visible posts on an enabled profile. Deleted
  tombstones are not rendered on profiles.
- Add a permitted post-detail API and SPA route. It displays author, content,
  timestamp, appropriate visibility/moderation state, accurate like count,
  whether the viewer liked it, and visible comments in chronological order.
- The existing global progress list is not redesigned into the future social
  feed in this task.

### Likes and comments

- Permit any active authenticated client, including the author, to like/unlike
  an accessible shared, non-hidden post. Enforce at most one like per client and
  post with a database uniqueness constraint and concurrency-safe behavior.
- Permit active authenticated clients to create trimmed plain-text comments of
  1–2,000 characters only on accessible shared, non-hidden posts. Derive the
  author from the verified Keycloak subject.
- A comment author may delete their own comment. A post author has no special
  authority over another client's comment. Hidden/private/deleted posts reject
  new cross-client likes/comments and are not usable to bypass post visibility.
- Post author deletion and full account erasure remove attached likes and
  comments in the approved lifecycle. Avoid orphaned relationships and ensure
  a deleted commenter disappears without reidentifying metadata.

### Moderation

- Extend the existing admin moderation area with separate, clearly labeled
  controls for shared comments and client biography/profile-picture content.
- Administrators may hide or restore with a required reason and delete with an
  optional reason. They may not edit user content, impersonate a client,
  follow/like/comment as a client, or change profile visibility/presence
  preferences.
- Hidden profile content is absent from other-client views and shown to the
  owner with its state/reason. A deleted profile picture removes its bytes; a
  deleted biography removes its content. Owners may supply replacement content
  normally after moderation.
- Audit only actor ID, target ID/type, action, timestamp, and reason. Never copy
  biography/comment text, image bytes, personal details, access tokens, or
  sensitive aggregates into audit/log records.

## Persistence and migration scope

Add only the tables/columns/indexes needed for:

- one social profile per Client, default-on visibility, optional nickname/bio,
  moderation state, and timestamps;
- one optional dedicated normalized profile-image record per Client with its
  own moderation/lifecycle metadata;
- unique directed follow edges with timestamps and self-follow protection;
- unique post likes with timestamps;
- post comments with author, post, content/moderation/deletion state, and
  timestamps;
- minimized social-moderation audit metadata where the existing audit pattern
  cannot represent the target safely.

Use UUID identities, foreign keys, uniqueness/check constraints, useful query
indexes, SQLAlchemy models, and Alembic migrations following repository
conventions. Backfill/lazily establish existing clients so their social profile
is visible by default without changing Task 23's default-off presence consent.
Do not add follower-count or like-count mutable counters as an independent
authority; derive counts from persisted relationships.

## API and service boundaries

- Keep profile policy, image lifecycle, follow graph, and interaction rules in
  focused service/domain logic; routers handle transport only.
- Provide owner profile read/update/image/visibility operations,
  viewer-authorized profile and list reads, follow/unfollow, post detail,
  like/unlike, comment create/delete, and administrator moderation operations.
- Reuse one policy projection for profile pages and the later feed. “Prepare for
  the feed” means avoiding duplicated visibility logic and providing stable
  service-level paginatable queries; it does not mean exposing or rendering a
  new global feed endpoint now.
- Use bounded pagination for follower/following lists, profile posts, and
  comments. Follow established repository conventions for parameters and
  response shapes; do not return unbounded social collections.
- Make direct API behavior match the UI. Browser-supplied ownership, author,
  follower, liker, commenter, or administrator IDs are never trusted.

## Frontend scope

- Redesign `/perfil` as the owner's social profile inside the existing
  ClientShell/navigation. Preserve the existing SPA behavior and avoid
  full-document navigation or activity-triggered UI flicker.
- Add read-only other-client profile, follower/following list, and post-detail
  routes. Reuse shared MUI components and Task 20 post cards; introduce a shared
  profile header/avatar pattern only if current primitives cannot express it.
- Clicking the owner's picture opens the accessible upload/change/remove flow.
  Other viewers cannot see edit affordances. Show upload validation, progress,
  success, failure, and fallback-avatar states in Portuguese.
- Clearly distinguish “Perfil visível para outros clientes” from “Mostrar no
  meu perfil quando eu estiver na academia.” Social visibility defaults on;
  presence sharing remains default-off and independent.
- Show follower/following counts and lists, follow/unfollow action on visible
  other profiles, newest-first posts, and a post detail with like count,
  like/unlike, comments, comment creation, and own-comment deletion.
- Extend the existing admin moderation UI without combining client and admin
  shells or exposing private posts.
- Verify phone, tablet, and desktop layouts, keyboard interaction, visible focus,
  semantic headings/landmarks, accessible names, touch targets, image alt text,
  dialogs, loading/empty/error states, and no ordinary horizontal scrolling.

## Authorization, privacy, and erasure

- Other-client social projections contain no e-mail, Keycloak subject, Account
  ID, Client ID, health/onboarding, training, attendance history, access events,
  biometrics, payment, credentials, or administrative data. The opaque social
  profile UUID is the only cross-client resource identifier.
- Do not infer presence from likes, follows, comments, profile access, login,
  recognition, or image data. Use only the implemented EXT-DEC-PRES-01
  projection.
- Update irreversible administrator account erasure to remove both incoming and
  outgoing follow edges, profile/image bytes, authored and received likes,
  authored comments, comments/likes attached to erased posts, moderation audit,
  existing posts/tombstones, and every other already-covered aggregate.
- Extend the exhaustive erasure test by seeding every new aggregate in both
  ownership directions and prove zero retained rows or image bytes can identify
  the erased client. Do not weaken the existing Keycloak-deletion behavior.
- Avoid user-authored content and image bytes in logs, exception messages, audit
  text, analytics, or test fixtures representing real people.

## Explicitly out of scope

- The future feed redesign/algorithm, a named-presence directory, suggested
  accounts, recommendations, trending content, discovery/search pages, or
  automatic ranking.
- Private follow requests, friend relationships, blocks, mutes, notifications,
  direct messages, sharing/reposting, hashtags, mentions, stories, rankings,
  leaderboards, or public/guest profiles.
- Automatic publication of training, health, attendance/presence, biometric,
  payment, credential, or administrative information.
- Changing anonymous occupancy, Task 23 presence derivation/consent, Keycloak
  profile/credentials, existing post private/shared semantics, or the physical
  access system.
- External media storage/CDN, camera capture, facial-recognition imagery, image
  generation, image filters, cropping editor, or content-recognition service.

## Expected tests and validation

Add focused backend domain/service, database/migration, API, authorization,
privacy, concurrency/idempotency, moderation, media-validation, and erasure
tests. Cover at minimum:

- existing/new default-on social visibility and independent default-off
  presence consent;
- owner-only edits/switch/image actions and cross-client hidden-profile denial;
- nickname/bio limits and image format, content, size, metadata, replacement,
  removal, and authorization behavior;
- self/duplicate follow denial, bidirectional erasure, hidden-profile reads,
  bounded lists, and inactive-client denial;
- owner versus viewer post projections and newest-first ordering;
- unique likes under retry/concurrency, comment ownership, private/hidden/
  deleted post denials, and post cascade behavior;
- administrator hide/restore/delete rules, reasons, owner feedback, and audit
  minimization;
- exhaustive account erasure leaving zero social records or image bytes;
- API responses/logs excluding prohibited identifiers and sensitive fields.

Add responsive frontend tests for owner, other viewer, hidden profile,
upload/fallback, follow lists, post detail, comment ownership, moderation, Task
23 presence separation, and Portuguese loading/empty/error states. Manually
inspect representative phone, tablet, and desktop layouts.

Run the repository-standard relevant backend and frontend suites discovered
from configuration, then at minimum:

```bash
git diff --check
git status --short
```

Review the full diff and confirm no future feed, public profile, sensitive-data
projection, camera behavior, payment feature, or unrelated refactor was added.

## Documentation and completion requirements

After implementation, mark only verified EXT-CA-SOC-02 criteria and Task 26
status complete. Record migrations/API/UI behavior, media dependency and
normalization, authorization/privacy evidence, erasure proof, tests, and manual
responsive checks. Do not rewrite Tasks 20 or 23 as though they originally
contained this later expansion.

Stop and ask if a materially new decision is discovered, including a need for
feed ranking/discovery, private follow approval, block semantics, notification
delivery, public profile access, a different media-storage service, or a new
content-retention policy. Do not commit or push.

## Ready-to-run implementation prompt

Read `AGENTS.md`, then
`docs/tasks/26-social-client-profile-and-post-interactions.md`, then only the
requirements, decisions, and completed task material listed under Required
reading. Inspect the existing Client, progress, presence, moderation, SPA, and
account-erasure implementations before editing. Implement only EXT-RF-SOC-02:
the default-on authenticated social profile, owner-managed nickname/biography/
profile picture, unilateral following, viewer-appropriate newest-first profile
posts, post-detail likes/comments, approved administrator moderation, and full
erasure integration. Preserve EXT-DEC-SOC-01 post visibility and
EXT-DEC-PRES-01 presence consent. Reuse Task 08/20/23 components, follow
`docs/frontend-design.md`, and check phone, tablet, and desktop. Prepare a shared
policy/query boundary for a future feed, but do not implement a feed, discovery,
recommendations, messaging, notifications, blocks, public profiles, sensitive
data publication, camera behavior, or payment functionality. Stop and ask if a
materially new human decision is required. Run relevant backend/frontend tests,
review the Git diff, and provide the AGENTS.md completion report. Do not commit
or push.
