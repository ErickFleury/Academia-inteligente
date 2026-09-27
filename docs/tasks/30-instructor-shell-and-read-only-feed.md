# Task 30 — Instructor Shell and Read-Only Feed

## Status

Implemented. Depends on Tasks 27 and 29.

## Objective

Create the dedicated instructor SPA shell, exact navigation/default routing,
bounded Perfil placeholder, and a read-only reuse of the existing social feed
for moderation-visible posts from public client profiles only.

## Requirements covered

- EXT-RF-INST-01: EXT-CA-INST-01.1–EXT-CA-INST-01.6.
- EXT-RF-SOC-02/03 only as existing feed, post-detail, privacy, media, and
  presentation boundaries reused without client interaction authority.
- RF-04/RF-05, RF-07/RF-08, and EXT-RF-LANG-01.

## Required reading

Read `AGENTS.md`, this task, and only: `docs/requirements.md`
EXT-RF-INST-01, EXT-RF-SOC-02, EXT-RF-SOC-03, RF-04, RF-05, RF-07, RF-08,
RN-04, RN-05, RN-11, RN-23, RN-28, RN-31, RNF02–RNF04, sections 2.1,
7.3, and 9.2, plus EXT-DEC-INST-01 and EXT-DEC-SOC-02/03;
`docs/instructor-role-specification.md` sections 2, 3, 13–15; Tasks 27 and 29
and their implementations/tests; `docs/frontend-design.md` shared shell,
social feed, responsiveness, and accessibility guidance.

## Exact implementation scope

- Add a reusable InstructorShell using the existing MUI theme/layout patterns,
  with navigation in this exact order: Feed, Planos pendentes, Meus planos,
  Todos os planos, Clientes, Equipamentos, Perfil. Do not add Início or a
  dashboard. An authenticated active instructor landing at `/` or the
  instructor area root is redirected to Feed.
- Add stable instructor routes for all destinations. Unimplemented destinations
  in this task may use explicit pt-BR “not yet available” states so later tasks
  can replace them; Perfil must remain only a future instructor-profile state.
- Extract/reuse the existing feed card, media, pagination, loading/error/end,
  and post-detail presentation rather than copying a second feed. An instructor
  projection returns only non-deleted, moderation-visible posts whose author
  social profile/account is public. Private-profile posts remain absent even if
  a client follower could see them.
- Instructor post detail may read the same permitted post and visible comments/
  media. It exposes no composer, edit, like/unlike, comment, delete, follow,
  profile-owner, or client-presence controls. Direct calls to every client
  social mutation remain denied.
- Resolve both Keycloak role and active local Employee server-side. A token with
  `instructor` but no active linked Employee fails closed. Clients, admins,
  attendants, inactive employees, and anonymous callers cannot use instructor
  routes merely by knowing URLs.
- Keep instructor social output minimized to what the permitted feed card/detail
  already needs. Do not expose e-mail, Client/Account IDs, health, training,
  attendance, private profile history/graph, or presence.

## Boundaries

- Do not create an instructor social profile, follower identity, feed aggregate,
  dashboard, notification, ranking, or mutation endpoint.
- Do not change client feed audiences or moderation rules.
- Later instructor destinations receive placeholders only; do not implement
  their business behavior here.

## Acceptance criteria and tests

Test default routing, exact desktop/mobile navigation and active state, local
Employee plus role authorization, public-profile inclusion, private-profile/
hidden/deleted exclusion, stable pagination, permitted detail/media/comments,
absence and direct denial of all social mutations, Perfil placeholder, pt-BR
copy, keyboard/focus behavior, and phone/tablet/desktop layouts. Reuse fixtures
from Task 27 and add instructor-specific policy tests.

Run targeted backend/frontend tests, `git diff --check`, and
`git status --short`; review for copied social policy or broadened visibility.

## Completion requirements

Update only relevant task/status documentation after verification. Report
files, tests/results, decisions, and unresolved issues. Do not commit or push.

## Ready-to-run implementation prompt

Use Terra with Medium reasoning. Read `AGENTS.md`, then
`docs/tasks/30-instructor-shell-and-read-only-feed.md`, then only its Required
reading. Inspect Tasks 27/29 and the current routing, shells, feed policy, media,
and post detail before editing. Implement only the instructor shell, exact
navigation/default Feed route, public-profile-only read-only feed/detail, and
Perfil placeholder. Reuse existing social services/components and deny every
instructor social mutation. Run targeted tests, review the diff, and provide the
required completion report. Do not commit or push.
