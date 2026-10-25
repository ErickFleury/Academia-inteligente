# Task 50: instructor review reading follow-up — 2026-10-24

The owner reported that the evidence workspace exposed JSON, hashes and internal
enum values without making source/rule/protocol review understandable.
This change implements existing EXT-CA-AI-02.23–25 and the pt-BR visual system;
it does not change professional approval, privacy or release requirements.

## Changes

- `frontend/src/components/evidence-review-material.tsx` presents original source
  links, selected quotations with citation locators and explicit original-language
  notices; proposed rules show parameters, open decisions, actual reference links
  and profile gaps. Public protocols show methods, thresholds, repetitions and
  budgets. Draft policy/dictionary/execution/accounting content is readable with
  field labels and explicit empty collections, outside JSON.
- `frontend/src/instructor-evidence-review-page.tsx` adds material-type filtering,
  an explanation of each category, honest absent-protocol feedback, professional
  review guidance and field help. The 37 current proposed rules have pt-BR
  navigation titles; NHS flexibility has a translated navigation title while
  retaining its original bibliographic title. Select controls explicitly render
  labels instead of API enums. Raw JSON/hash metadata is an optional collapsed
  technical disclosure. Source text and research prose remain in the original
  language; no translation is claimed as an official or reviewed interpretation.
- The page regression file and new material-component test file verify source
  links/quotations, executable-link denial, rule parameters/references/gaps,
  public protocol reading, incomplete bundles, filters, empty protocol state,
  localized selected values and existing judgment/custody/privacy behaviors.
- `docs/frontend-design.md` and the instructor workflow guide document the
  readable material boundary. No backend, database, judgment records or approval
  requirements changed; no dependency, commit or push was added.

## Verification and limits

Frontend lint and production build pass (existing bundle-size advisory).
The latest focused run has **11 passing tests and two five-second timeouts**:
complete judgment registration and complete custody registration. No timeout or
assertion was relaxed; independent field edits retain real change events and
checks for associated labels. All five material-reading tests pass, as do the
category/empty-protocol and current session/privacy/approval-blocking checks.
Earlier runs also encountered these integration timing failures; this follow-up
does not claim a fully green regression suite. The earlier 312-test full result
predates this readability change and must not be presented as its validation.

The existing browser-control environment has no available browser, so no visual,
keyboard, responsive or intended-user acceptance is claimed. The local Vite
application consumes these source changes; refreshing the evidence page loads
the new presentation. Scientific review and actual evaluation remain separate.
