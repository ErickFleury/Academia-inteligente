# Project inspection — 2026-09-27

Requested scope: inspect vulnerabilities, deprecated implementation and errors;
fix verified issues and commit each completed group. The preceding pilot setup
was checkpointed as `3d28fbf`; owner webcam verification remains pending.

## Requirements and review scope

RF-04/05 authorization, RF-09/10 secure invitation access, EXT-RF-SOC-01/02/03
media/moderation/privacy, EXT-RF-INST-03 collection cursors, EXT-RF-FACE-01 and RF-20/23/24 occupancy integrity;
RN-02/03/04/05/10/23/27/28/29/32/34; RNF01/04/05/06. No new product feature or
role is introduced. Existing functional boundaries and the canonical technology
baseline remain authoritative.

Reviewed browser OIDC handling, backend identity/role gates, social ownership
and media routes, biometric transport/provider lifecycle, occupancy writers,
onboarding invitation transport, external AI/CEP adapters, dependency manifests,
container configuration, tests and lint/build scripts.

## Findings and fixes

| Finding | Impact | Resolution / state |
| --- | --- | --- |
| Pillow 11.1.0 has published vulnerabilities | Image parsing/processing vulnerabilities, with exploitability varying by format/code path | Updated existing dependency to 12.3.0; decoder allowlists applied before opening uploads. Rebuilt backend audit reports no known Python vulnerabilities. |
| Social upload byte limits ran after framework buffering | Oversized/chunked uploads could allocate unbounded request memory before validation | Enforce existing 5 MiB limit before framework buffering; reject unsupported decoders and oversized decoded dimensions, convert bomb warnings/errors to controlled failures. |
| Comment-image endpoint checked the parent post but not comment moderation/deletion | A known image URL could expose a hidden comment's attachment | Media now follows the same parent/comment policy as the comment list, including its existing owner exception. |
| Protected API responses lacked explicit cache restrictions | Private media/results could remain in ordinary response caches after visibility changes | API responses use `Cache-Control: no-store` and `X-Content-Type-Options: nosniff`. |
| Browser token refresh can finish after logout/timeout | Cleared session can be restored by late network responses | Generation/session checks reject late responses, refreshes are deduplicated and current activity is preserved. |
| Invitation tokens included in API query strings | Tokens could enter API request logs and referrers | Use a bounded request header; browser referrers suppressed. E-mail links and intentional redemption remain unchanged. |
| Malformed identity-provider responses | Unexpected JSON types could produce errors or misinterpret roles | Bounded reads and strict payload validation fail closed. |
| Frontend lint checked an empty root project | The lint command could pass without checking application files | Run TypeScript project references; document language corrected to pt-BR. |
| Social moderation omitted `target_id` from its request schema and required a local administrator Account | Valid requests failed instead of moderating | Restore required target UUID; accept the authenticated OIDC-only bootstrap administrator and record its subject. |
| Moderation did not verify shared/public eligibility, and the older post route omitted audits | A known private target could be changed; audit records were inconsistent | Consolidate both routes behind one policy and audit transaction; private targets are rejected. |
| Biography moderation assigned non-mapped attributes | Hiding a biography did not persist or affect visibility | Write the actual biography moderation columns. |
| Full erasure missed profile-target and actor audit records | Residual personal metadata or a foreign-key failure could prevent complete erasure | Delete relevant audits, preserving unrelated content and shared-employee history. |
| Legacy occupancy writers remained callable in pilot mode | Count/freshness could diverge from the pilot's person-state ledger | Reject legacy external passages, external heartbeats and aggregate corrections while pilot mode is active; retain their disabled-mode contract. |
| Invalid cursor types and empty text-only posts could raise uncaught errors | Invalid requests became server errors | Bound and type-check social/training cursors; return controlled post-validation errors. |
| Legacy SQLAlchemy Query mutation API | Maintenance debt in privacy/media mutations | Use SQLAlchemy 2 update/delete statements with synchronized session state. |
| Keycloak pinned at 26.6.3 | Upstream security fixes exist after this release | Separate canonical-version decision; proposal below. |

The social decoder input allocation limit is 4096×4096 pixels in total; accepted
JPEG/PNG/WebP are still normalized to at most 1024×1024. No actual malicious native
decoder exploit is executed. Regression tests use bounded fixtures and validate
that unsupported decoders are never called.

## Dependency evidence

- `npm audit --json`: zero reported vulnerabilities in the resolved frontend tree.
- Initial `pip-audit`: only Pillow was flagged; its 33 advisory entries include
  aliases/duplicates and represent 17 distinct CVE identifiers, not 33 distinct
  application exploits. The replacement 12.3.0 clears the installed Python audit.
- Audit tooling was installed only in disposable containers, not project
  requirements. No new application dependency was added.
- Primary Pillow evidence: [12.3.0 security fixes](https://pillow.readthedocs.io/en/stable/releasenotes/12.3.0.html),
  [security guidance](https://pillow.readthedocs.io/en/stable/handbook/security.html).
- These results do not certify the full OS/native-library contents of all
  third-party Docker images or unknown vulnerabilities. The isolated CompreFace
  image/model boundary remains as approved; no provider/model replacement occurs.

## Keycloak upgrade proposal — decision pending

Proposed exact change: `quay.io/keycloak/keycloak:26.6.3` → `26.7.4`, with the
same realm, hosted theme, OIDC clients and roles. Update the corresponding
canonical baseline and supporting decision history together if approved.

[26.7.2 release notes](https://www.keycloak.org/2026/08/keycloak-2672-released)
include a reset-credentials bypass and permission/secret-exposure fixes.
[26.7.4 release notes](https://www.keycloak.org/2026/09/keycloak-2674-released)
include unauthenticated locale-cache denial of service and other security fixes.
Not every listed advisory is reachable in this local configuration; feature-level
exposure must not be equated with the whole upstream CVE list.

`docs/requirements.md` §6.1.1 explicitly says: “The pinned versions above are
canonical” and “This document does not authorize upgrades.” Therefore this
inspection does not silently change that pin or migrate the persisted realm.
The concrete follow-up is: review the official migration guide, validate the
repository theme and OIDC/provisioning flows on an isolated copy, preserve local
realm recovery material outside Git, then upgrade/recheck login and provisioning.
No new identity reset is part of that upgrade.

## Verification

Results are recorded per checkpoint below as checks finish. No real facial
capture, live hardware release or additional test-account reset is performed.

- Upload/media checkpoint: **355 backend tests passed**, including PostgreSQL,
  decoder allowlist, decompression limits, streaming byte limits and private/hidden
  comment-image regressions. Full Ruff and Git whitespace review passed.
  Backend rebuilt with Pillow 12.3.0; installed Python audit returned no findings.

- Session/invitation checkpoint: full frontend suite **146 passed**, plus the
  callback retry regression verified separately; **23 targeted backend tests**
  passed. Production frontend build and full Ruff passed. Existing large-bundle
  warning remains; no new dependency was introduced. Callback codes are removed
  from the browser URL even when authentication fails.

- Moderation/occupancy/input checkpoint: **377 full backend tests passed**,
  including PostgreSQL migration preservation, refusal of a lossy downgrade,
  audit erasure, bootstrap-administrator moderation, private-target rejection,
  biography hiding, malformed cursors and pilot writer isolation. Full Ruff,
  TypeScript project lint and Git whitespace review passed. Frontend totals are
  **147 tests** after the additional callback retry test (146 full-suite passes,
  followed by all 28 application tests).
- Applied additive migration `20260927_29` locally and restarted the backend.
  Health returned HTTP 200; live OpenAPI confirms the invitation header and
  required moderation target, and the database reports the expected revision.

## Changed-file map and operational notes

- Backend dependency/HTTP/image changes: `backend/requirements.txt`,
  `backend/app/http_security.py`, `backend/app/main.py`,
  `backend/app/modules/biometrics/images.py`, and social media/service/router files.
- Authentication/invitation changes: backend identity service and onboarding
  router; frontend `auth.ts`, `app.tsx`, `onboarding-access.ts`, `index.html`,
  and `package.json` lint script.
- Moderation/privacy changes: social models/service/router, progress
  service/router, client erasure service, and migration
  `backend/alembic/versions/20260927_29_social_moderation_actor.py`.
- Occupancy and malformed-input changes: occupancy router and training
  collection cursor parser. Related existing tests were extended; new suites
  cover HTTP/media security, identity responses and moderation/security migration.
- Existing moderation audit rows remain valid. New rows record the verified
  OIDC subject, with a local Account reference when available. Downgrading the
  new schema deliberately refuses when subject-only audits exist, instead of
  deleting history or inventing administrator Accounts.
- API invitation validation/redemption now require `X-Onboarding-Token` (at most
  512 characters). GET remains non-consuming; POST remains explicit redemption.
  E-mail entry URLs are unchanged. The SPA suppresses referrers.
- No production deployment, identity reset, new package/provider, biometric
  model change or real turnstile call was performed. The owner webcam checklist
  remains pending. The pinned Keycloak upgrade is the remaining security
  decision; full third-party container OS/native scans and real-camera manual
  acceptance remain outside the evidence collected here.
