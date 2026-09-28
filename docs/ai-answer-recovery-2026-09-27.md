# AI answer recovery — 2026-09-27

Scope: EXT-RF-AI-01, RF-11–13 and privacy-safe diagnostics for the existing
RF-18/provider integration, under the approved answer-recovery amendment.

## Parsing, speed and recovery checkpoint

- Complete personal measurement clauses support units, common Portuguese kilo
  spellings and omitted units when the preceding question identifies the field.
  Goals, other people's measurements, medications, questions, unsupported units,
  ambiguous alternatives and invalid schema values are not accepted as measurements.
- Clear measurements, short categorical answers and explicit corrections bypass
  the provider only if the entire message is recognized. Mixed/free-form context
  continues through the model. No model/version/dependency changes.
- Uncertain or conflicting measurements can be proposed for explicit confirmation.
  The proposal is not a verified answer. Confirmation is bound to expiring client
  state, is superseded by form edits and cannot survive conversation expiration.
- Failed answers receive clarification instead of a bare repeated question. Two
  unsuccessful answers to the same question expose direct measurement entry or
  the existing form. Other collected answers remain intact. Replayed requests do
  not increment failure counters. Final completion remains a separate client action.

Changed files: onboarding evidence, direct-answer and measurement parsers,
conversation/state/draft services, additive response contract, frontend conversation
API/page, related backend/frontend tests, requirements and decisions.

Validation: 507 backend tests passed including real PostgreSQL concurrency;
six onboarding frontend tests passed; frontend production build passed (existing
bundle-size warning remains). A read-only replay confirmed that both originally
rejected numeric replies now match the direct parser, without a model call or
changes to the client's data. The later unrelated reply was excluded from that
check. Complex wording still requires model interpretation or clarification.

## Diagnostics checkpoint

`backend/app/integrations/ai_diagnostics.py` emits allowlisted JSON metadata through
the existing Uvicorn console logger. Onboarding and training chat emit `ai_turn`;
the shared adapter emits `ai_provider_call` for each actual provider attempt.

Fields distinguish operation, direct/model/confirmation/cached path, elapsed
milliseconds, controlled outcome/reason, retry count, accepted-field count and
fallback visibility where applicable. There are no messages, answer values,
field names, account/conversation/request IDs, endpoints, credentials, raw
provider errors or exception tracebacks in these diagnostic events. Per-turn
metadata uses isolated execution context and is reset on completion/failure.

Examples of reasons: `multiple_measurements`, `invalid_measurement`,
`uncertain_answer`, `conflicting_answer`, `timeout_or_network`,
`malformed_structured_output`. A successful HTTP response can now be distinguished
from a turn that asked for clarification. Cached requests do not count as new
model attempts. Inspect only these events with:

```sh
docker compose logs --since 30m backend | rg '"event":"ai_(turn|provider_call)"'
```

Changed files: the diagnostic helper, provider adapter, onboarding and training
chat orchestration, diagnostic regression tests and this report. Focused check:
82 tests passed for diagnostics, direct answers, training chat and AI adapters.
Privacy tests include prompt/answer/error sentinels and concurrent context isolation.
No new database records or retention policies were introduced for diagnostics;
normal Docker operational-log retention applies. Free-form messages still use
the configured model and its existing timeout/retry policy.

Final validation: all 512 backend tests passed, including PostgreSQL concurrency
and diagnostic privacy coverage. The final confirmation-safety focused run passed
49 tests. Ten synthetic service-level measurement turns in disposable in-memory
databases made zero provider calls: median 8.40 ms, maximum 12.72 ms. These timings
exclude browser/network latency and do not predict model-backed response time.
No live client answers were repaired or replayed into persistent state. No
unresolved implementation blockers; complex phrasing may still need clarification.
