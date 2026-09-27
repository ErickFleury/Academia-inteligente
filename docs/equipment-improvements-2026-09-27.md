# Equipment registration and visual refresh

Scope: RF-32/33, EXT-RF-EQP-01, EXT-RF-INST-05, EXT-RF-LANG-01;
RN-04/05/20/33, RNF01/02/03/04/06. Owner approved all seven proposed improvements
and all equipment pages. Brand, manufacturer model, category, location and serial
number remain administrator-only. Photos support upload and existing links.

## Checkpoints

1. Backend: atomic model/initial-unit registration; 1–100 unit batches with
   collision-free generated labels under the existing model row lock; private
   metadata; normalized PostgreSQL photos; active-only public media; instructor
   search before pagination; additive migration 30. Complete. The affected suite
   passed 55 tests. Full backend run passed 394 tests and found the reset-table
   allowlist dependency; both reset tests passed after adding photo preservation.
   No live pilot reset was performed.
2. Administrator UI: searchable compact inventory, details drawer, two-step
   registration, editable private details and unit identifiers, photo preview,
   recoverable upload, batch addition and confirmed inventory changes. Complete.
   Eight workflow regressions and production build passed. Firefox checked list,
   detail, units, registration and review at 360×800, 768×1024 and 1366×768; no
   horizontal overflow, unlabeled controls or sub-44px buttons were found.
3. Instructor and public/client UI: focused operational workspace and responsive
   catalog cards, search and useful empty/error states. Complete. Eight related
   tests passed, including StrictMode loading and query-preserving pagination.
   Firefox verified all three surfaces at the target sizes, keyboard activation,
   dialog Escape/restore-focus and mobile return-to-list focus.
4. Responsive, keyboard, regression and live local verification. Complete.
   Full frontend suite: **159 passed**. Backend coverage: **395 distinct tests**
   passed across the full run and the targeted reset rerun described above.
   Production build, TypeScript checks, Ruff and Git whitespace checks passed.
   Local migration `20260927_30` applied, backend restarted, HTTP health 200,
   batch/photo API contracts confirmed in live OpenAPI. Temporary browser
   fixtures removed; visual checks used synthetic browser data and did not
   create or remove real inventory.

## Boundaries

No new package or external provider. The shared ordinary-image decoder retains
its 5 MiB byte limit, JPEG/PNG/WebP allowlist, 4096×4096 total input-pixel limit,
metadata stripping and 1024×1024 output bound. It never handles face enrollment.
Legacy model creation without initial units remains supported. No existing
training plan is modified. Equipment changes do not alter attendance/biometrics.
Keycloak remains pinned as requested.

## Delivery and changed files

- Backend checkpoint `a8321ed`: equipment models/service/admin/instructor routers,
  migration 30, shared `app/media_images.py` decoder and upload-size middleware.
  Social image normalization delegates to the same decoder without policy changes.
  The pilot reset allowlist/test was updated only to preserve equipment photos.
- Administrator checkpoint `1aa0757`: `equipment-management-page.tsx`,
  `equipment-editor.tsx`, `equipment.ts`, shared equipment presentation, and
  workflow/photo-recovery tests.
- Instructor/catalog checkpoint `abd3e4a`: instructor equipment page/API client,
  public/client catalog, tests and an optional wider public-shell content area.
- Canonical requirements, supporting decisions and frontend design guidance
  record the approved metadata/privacy and interaction choices.

## Remaining limitations

The existing large-JavaScript-bundle build warning remains non-blocking. Image
links depend on the referenced host; uploads avoid that dependency. No new
product decisions are pending for this equipment scope. The separate owner
webcam checklist and deferred Keycloak upgrade remain outside this change.
