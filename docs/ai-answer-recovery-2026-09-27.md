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
