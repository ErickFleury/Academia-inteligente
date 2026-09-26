# Task 27 — Authenticated Chronological Social Feed

## Status

Planned. EXT-DEC-SOC-03 is resolved and this task is ready for implementation.

## Objective

Redesign the authenticated client “Progresso” destination as the bounded social
feed approved by EXT-RF-SOC-03. Reuse ProgressUpdate, the Task 26 social-profile
and interaction foundations, and the existing client/admin shells. Add a
private-by-default post composer with bounded image attachments, a stable
newest-first cursor feed, always-visible interaction counts, post detail with
newest-first comments and comment media, author editing, whole-aggregate
moderation, and complete erasure coverage.

This task implements a chronological authenticated feed, not a recommendation
system or a public social network. It preserves EXT-DEC-SOC-01 post visibility,
EXT-DEC-SOC-02 profile/privacy foundations, and EXT-DEC-PRES-01 presence
consent except for the amendments stated in EXT-DEC-SOC-03.

## Requirements covered

- EXT-RF-SOC-03: EXT-CA-SOC-03.1–EXT-CA-SOC-03.10.
- EXT-RF-SOC-01 only as the existing ProgressUpdate ownership, visibility,
  moderation, deletion, and tombstone behavior extended with media and feed
  queries.
- EXT-RF-SOC-02 only as the existing social-profile, profile navigation,
  likes/comments, moderation, and erasure behavior integrated with the feed.
- EXT-RF-PRES-01 only to preserve independent consent and prevent feed activity
  from becoming evidence of physical presence.
- EXT-RF-LANG-01 for all new user-visible and accessible text.

## Related rules and approved decisions

- RN-04/RN-05: derive client and administrator identity server-side and enforce
  author, viewer, interaction, media, moderation, and erasure authorization in
  the backend.
- RN-11/RN-23/RN-28/RN-33: exclude sensitive data from social projections,
  logs, audits, URLs, cursors, and retained deletion state.
- EXT-DEC-SOC-01 remains authoritative for ProgressUpdate private/shared
  ownership and its contentless deletion tombstone.
- EXT-DEC-SOC-02 remains authoritative for social profiles, opaque public-facing
  profile IDs, following, likes/comments, moderation, and erasure foundations.
- EXT-DEC-SOC-03 is authoritative for feed ordering, media, edits, the
  shared-to-private guard, private-profile author shells, newest-first comments,
  and whole-aggregate moderation.
- EXT-DEC-PRES-01 remains independent. A post, comment, like, profile view, or
  feed request never opts a client into identifiable current presence.
- DEC-17 remains unchanged: Account and Client identities are independent and
  Keycloak continues to own authentication credentials.

## Prerequisites and dependencies

- Tasks 08, 20, 23, and 26 are implemented and their migrations are applied.
- Inspect the current ProgressUpdate, social profile, post detail,
  likes/comments, media, moderation, SPA routing, and exhaustive
  account-erasure implementations and tests before editing.
- Reuse the MUI theme, shared components, ClientShell/AdminShell, authorization
  dependencies, service/transaction patterns, and Alembic conventions.
- Repair a prerequisite defect only when it directly blocks EXT-RF-SOC-03 and
  report it separately; do not broaden this task into a Task 26 rewrite.

## Required reading

Read `AGENTS.md`, then this task, then only the following material:

- `docs/requirements.md`: EXT-RF-SOC-01, EXT-RF-SOC-02, EXT-RF-SOC-03,
  EXT-RF-PRES-01, EXT-RF-LANG-01, RF-03–RF-05, RN-04, RN-05, RN-11, RN-23,
  RN-28, RN-33, RNF02–RNF04, sections 7.1.1, 7.3, 9.1, and 9.2;
- `docs/decisions.md`: EXT-DEC-SOC-01, EXT-DEC-SOC-02, EXT-DEC-SOC-03,
  EXT-DEC-PRES-01, DEC-16, and DEC-17;
- `docs/product-extensions.md`: EXT-RF-SOC-01, EXT-RF-SOC-02,
  EXT-RF-SOC-03, and EXT-RF-PRES-01;
- `docs/frontend-design.md`: shared foundations, ClientShell/AdminShell,
  progress sharing, Social profile, Social feed, Feed composer, Feed media,
  Post detail and comments, Infinite loading, Imagery/responsiveness/
  accessibility, and Social-feed research basis;
- completed Tasks 08, 20, 23, and 26 plus their current implementations and
  directly related tests;
- the current administrator social-moderation and exhaustive account-erasure
  implementations and tests.

Do not treat older Task 20/26 feed deferrals or Task 26 chronological-comment
wording as current policy; EXT-DEC-SOC-03 is their narrow later amendment.

## Exact implementation scope

### Feed query and route

- Keep `/progresso` inside ClientShell and replace its prior list presentation
  with the chronological feed. Do not create a second post aggregate or copy
  post content into feed-specific rows.
- Return only shared, non-deleted, moderation-visible posts permitted to the
  active authenticated client. Include shared posts from private profiles.
- Order deterministically by `(created_at DESC, id DESC)`. Use bounded pages
  and an opaque continuation cursor that encodes no sensitive identity or
  client-trusted authorization decision.
- Make cursor application stable under concurrent inserts, avoid offset-based
  skipping/duplication, reject malformed cursors safely, and return an explicit
  end state. The service/query policy is shared with profile and post-detail
  projections rather than duplicated in the router.
- Do not rank, score, personalize, recommend, trend, filter by followed users,
  or insert advertisements. Infinite loading changes page delivery only.

### Post composer and card

- Place one full composer at the top. It creates a ProgressUpdate owned by the
  authenticated client; ignore any browser-supplied author identity. The same
  aggregate appears in the author's permitted profile history without copying
  it into a feed-specific record.
- Accept trimmed plain text up to 2,000 characters, zero to four ordered images,
  or both. Text or at least one image is required, so image-only posts are
  valid. Preserve private as the default and require an explicit choice to
  publish as shared.
- When the composer leaves the viewport, show one compact fixed “Criar
  publicação” action at a safe screen edge. Activating it returns to and focuses
  the original composer. It must not create another composer, draft, or form,
  and it disappears while the full composer is visible.
- Each feed card shows a keyboard-operable author avatar and presentation
  username, localized timestamp, text, ordered media, “editado” when applicable,
  and accurate like and visible-comment counts/actions without hover.
- Clicking the card's detail affordance opens the existing post-detail route.
  Clicking an author avatar or username opens their opaque social-profile route.

### Post and comment media

- Add dedicated ordered post-image records and optional comment-image records;
  do not store image bytes, base64, external URLs, or host paths in
  ProgressUpdate/PostComment/Client/Account columns or ordinary JSON.
- Accept only static JPEG, PNG, or WebP input up to 5 MiB per image. Decode and
  validate actual content, reject malformed/animated/unsupported files,
  normalize orientation, strip metadata, bound dimensions within 1024×1024
  while preserving aspect ratio, safely re-encode, and store media type,
  dimensions, position where relevant, lifecycle timestamps, and bytes in
  PostgreSQL.
- Serve bytes only through viewer-authorized media endpoints. The frontend may
  create and revoke blob URLs; credentials and stable storage paths never
  appear in image URLs.
- Preserve order for post images, enforce four/one limits in service and
  database invariants where practical, and remove all replaced, removed,
  deleted, moderated, or erased bytes transactionally.
- Reuse the approved Task 26 image pipeline where its validation and
  normalization semantics match. Do not add object storage, CDN, camera access,
  crop/filter tools, generated imagery, or content-recognition services.

### Post detail and comments

- Reuse post detail and show all feed-card content plus authorized actions.
  Visible comments are ordered `(created_at DESC, id DESC)` and paginated.
- Each comment shows a keyboard-operable commenter avatar/presentation username,
  localized timestamp, text and/or one image, “editado” when applicable, and
  authorized edit/delete controls.
- Place one accessible comment composer after post actions and before the list.
  It accepts trimmed plain text up to 2,000 characters, one image, or both;
  image-only comments are valid. Label the send action “Enviar comentário.”
- Do not add replies, reply identifiers, indentation implying threads, or a
  second comment level.

### Author editing and visibility transitions

- Only the author may edit their post or comment. Permit text changes and
  attachment addition, replacement, removal, or reordering within the limits.
  A resulting aggregate must still contain text or media.
- Delete superseded bytes in the same transaction. Set `edited_at` only for a
  user-facing content/attachment change and display “editado”; do not expose
  an edit-history body or use moderation actions as author edits.
- A shared post with any retained, non-deleted comment cannot become private,
  regardless of whether comments are visible or moderation-hidden. Return a
  clear pt-BR domain error from direct API and UI flows.
- Likes do not prevent a shared post becoming private. Retain those like rows,
  hide them and disable cross-client reads/interactions while private, and make
  them visible again if the post is reshared. Private or hidden posts reject
  new cross-client likes/comments and media reads.

### Profiles and private-profile state

- Profile visibility and post visibility are independent: a private profile's
  shared post remains eligible for the authenticated feed.
- For a private profile, its author link opens a deliberate private-profile
  shell exposing only the presentation username—nickname when available,
  otherwise the existing client name—and the currently permitted profile
  picture or fallback avatar. Do not expose biography, follower/following graph,
  presence, profile post history, e-mail, or internal identity.
- This minimized shell remains authenticated-only and is not a public/guest
  profile. Presence is shown only where EXT-DEC-PRES-01 separately permits it.

### Moderation, deletion, and erasure

- Extend the existing administrator social-moderation surface for whole shared
  post and whole shared comment aggregates, including attachments. Hide/restore
  requires a reason; permanent deletion accepts an optional reason.
- Administrators do not edit text/media, impersonate authors, change
  visibility, or interact as clients. Audit only actor ID, opaque target
  ID/type, action, timestamp, and reason; never copy content or image bytes.
- Post deletion removes post images, likes, comments, and comment images and
  retains only the approved contentless tombstone and minimum audit metadata.
  Comment deletion removes its text/image from client projections.
- Extend irreversible account erasure to remove every authored post/tombstone
  and image, authored comment/image, authored/received like and comment
  relationship attached to erased posts, related social moderation audit, and
  every already-covered Task 26 aggregate. Prove that no bytes or cursor/cache
  projection can reidentify the erased client after a subsequent read.

## Persistence, API, and service boundaries

- Add only the columns/tables/indexes/constraints required for ordered post
  images, comment images, author edits, stable cursor queries, and their
  lifecycles. Use UUIDs, foreign keys, cascading/restrictive behavior chosen to
  preserve the approved tombstone and erasure rules, and Alembic conventions.
- Keep authorization and visibility in reusable policy/service/query code;
  routers handle transport and never trust owner/viewer/author/admin IDs from
  the browser.
- Provide bounded feed/comment reads, authorized media reads, post/comment
  create/edit/delete, post visibility mutation with the comment guard, and
  moderation operations. Preserve idempotent like behavior and accurate counts.
- Avoid N+1 author/count/media queries and unbounded collection loading. Counts
  are derived from persisted relationships rather than mutable client-trusted
  counters.
- Error bodies, logs, OpenAPI examples, cursors, tests, and audit records must
  not include tokens, content bytes, sensitive aggregates, Account/Client UUIDs,
  Keycloak subjects, or real personal data.

## Frontend and responsive behavior

- Follow the Social feed patterns in `docs/frontend-design.md` rather than
  copying another network's layout. Use a centered single reading column,
  existing theme/components, and pt-BR application text.
- Manage selected-file previews and fetched blob URLs safely, revoke object
  URLs on replacement/unmount, preserve stored aspect ratios to prevent layout
  shift, and provide image loading/failure/fallback states.
- Load the next cursor page with an IntersectionObserver sentinel while also
  exposing a keyboard/screen-reader-operable “Carregar mais publicações”
  fallback. Prevent duplicate requests and de-duplicate overlapping pages by
  opaque post ID without moving focus or replacing read cards.
- Use semantic articles/comments, logical headings and landmarks, `aria-busy`
  during append, announced loading/error/end states, visible focus, accessible
  names, keyboard-dismissible dialogs if used, and usable touch targets.
- Verify the formal DEC-16 phone, tablet, and desktop viewports. Ensure the
  composer return action does not cover bottom navigation or card actions and
  that no ordinary horizontal scrolling is introduced.

## Explicitly out of scope

- Recommendation/ranking algorithms, followed-only ranking, discovery/search,
  suggested accounts, trending content, advertisements, or analytics expansion.
- Replies/threading, reposts/sharing, mentions, hashtags, stories, reactions
  beyond the existing like, saved posts, polls, or live content.
- Private follow requests, friend relationships, blocks, mutes, notifications,
  direct messages, or public/guest profiles.
- Automatic publication of training, health, attendance/presence, biometric,
  payment, credential, or administrative information.
- Camera behavior, face recognition, image generation/editing/filters, external
  media hosting/CDN, or payment functionality.
- Changes to Keycloak credential ownership, the physical access system, or
  EXT-DEC-PRES-01 consent and derivation.

## Expected tests and validation

Add or update focused backend domain/service, migration, API, authorization,
privacy, concurrency, media, moderation, and erasure tests. Cover at minimum:

- private-by-default publishing; text-only, image-only, and mixed posts;
- feed-created posts appearing in the author's permitted profile history;
- zero/four/five post-image and zero/one/two comment-image boundaries;
- content decoding, type/size/animation/dimension/metadata behavior and
  authorized media reads;
- stable newest-first cursor pages, ties, concurrent insertion, malformed/end
  cursors, page bounds, de-duplication, and forbidden data absence;
- shared posts from private profiles and the exact two-field private shell;
- accurate always-visible counts, like idempotency, and newest-first comments;
- author-only text/attachment edits, validation after removals, byte cleanup,
  and `edited_at`/“editado” behavior;
- retained comments blocking shared-to-private changes while likes do not,
  including like invisibility and restoration across private/reshared states;
- whole-post/comment hide, restore, deletion, media cleanup, tombstones, audit
  minimization, and direct-API authorization;
- exhaustive bidirectional account erasure leaving no identifying rows or
  media bytes and no stale authorized projection;
- independent presence consent and prohibited sensitive-data/log exposure.

Add frontend tests for composer validation/media previews, the compact return
action and focus, ordered cards, persistent counts, cursor append/retry/end,
post detail, newest-first image comments, editing, private-profile navigation,
moderation states, inaccessible media, and Portuguese loading/empty/error
feedback. Manually inspect and record phone, tablet, and desktop results.

Run the repository-standard directly related backend and frontend suites, then
at minimum:

```bash
git diff --check
git status --short
```

Review the full diff and confirm no algorithm, replies, discovery, messaging,
notifications, blocks, guest profile, sensitive publication, camera behavior,
payment functionality, or unrelated refactor was added.

## Documentation and completion requirements

After implementation, mark only verified EXT-CA-SOC-03 criteria and Task 27
status complete. Record migrations and API/UI behavior, query/cursor policy,
media lifecycle, authorization/privacy evidence, moderation/erasure proof,
tests, and manual responsive checks. Do not rewrite Tasks 20 or 26 as though
they originally included this later expansion.

Stop and ask if implementation requires a materially new human decision,
including a new content audience, image format/limit/storage provider,
retention policy, recommendation/ranking behavior, reply structure, notification,
block/private-follow policy, public access, or sensitive-data publication. Do
not commit or push.

## Ready-to-run implementation prompt

Read `AGENTS.md`, then
`docs/tasks/27-authenticated-chronological-social-feed.md`, then only the
requirements, decisions, completed task material, and implementation/tests
listed under Required reading. Inspect the existing progress, social-profile,
post-detail, interactions, moderation, media, SPA, and account-erasure code
before editing. Implement only EXT-RF-SOC-03: redesign `/progresso` as the
authenticated private-by-default chronological social feed, add the top
composer and compact scroll-return action, support up to four post images and
one comment image including image-only content, use opaque cursor pagination,
show counts without hover, navigate author identity to the permitted full or
private profile, order comments newest-first, allow author-only text/attachment
editing with “editado,” enforce that retained comments—but not likes—block a
post becoming private, and extend whole-post/comment moderation and complete
account erasure. Preserve EXT-DEC-SOC-01, EXT-DEC-SOC-02, and independent
EXT-DEC-PRES-01 consent except where EXT-DEC-SOC-03 explicitly amends them.
Reuse Tasks 08/20/23/26 and follow `docs/frontend-design.md`; verify phone,
tablet, desktop, accessibility, authorization, privacy, media cleanup, and
cursor stability. Do not implement ranking, recommendations, replies,
discovery, messaging, notifications, blocks, public profiles, sensitive-data
publication, camera behavior, or payment functionality. Stop and ask if a
materially new human decision is required. Run relevant backend/frontend tests,
review the Git diff, and provide the AGENTS.md completion report. Do not commit
or push.
