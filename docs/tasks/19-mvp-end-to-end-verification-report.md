# Task 19 — MVP End-to-End Verification Report

**Date:** 2026-09-23
**Environment:** local Docker Compose runtime; controlled SQLite/ASGI test
fixture for the cross-module contract; no live AI, SMTP, or Keycloak service
was used by automated tests.
**Scope:** RF-01–RF-05, RF-09–RF-13, RF-15–RF-19, EXT-RF-AI-01, and
EXT-RF-LANG-01 only.

## Evidence and commands

| Check | Command | Result |
| --- | --- | --- |
| New critical-path contract | `docker compose run --rm backend ruff check tests/test_mvp_end_to_end_verification.py` and `docker compose run --rm backend pytest -q tests/test_mvp_end_to_end_verification.py` | Passed; 1 test |
| Backend regression suite | `docker compose run --rm backend pytest -q` | Passed; 97 tests in 3.86 s |
| Frontend type check | `docker compose run --rm frontend npm run lint` | Passed |
| Frontend regression suite | `docker compose run --rm frontend npm test` | Passed; 39 tests in 8 files |
| Frontend production build | `docker compose run --rm frontend npm run build` | Passed; Vite reported a non-blocking 500 kB chunk-size warning |
| Repository-wide backend lint | `docker compose run --rm backend ruff check .` | **Unresolved pre-existing formatting failures** in migrations `20260922_08_add_training_ai_conversations.py`, `20260923_09_add_training_adaptation_proposals.py`, and `20260923_10_add_training_chat_adaptation_suggestions.py`. No Task 19 file caused this failure. |

`backend/tests/test_mvp_end_to_end_verification.py` exercises one complete
client journey with a mutable OIDC identity and compatible local AI adapters:
identity-derived ownership; authoritative onboarding completion; safe initial
proposal; instructor approval/activation; client-only current-plan and chat
access; an explicitly confirmed/instructor-approved adaptation; version
persistence after reauthentication; cross-client denial; client denial of an
administrative endpoint; and controlled AI failure without current-plan
corruption. It uses no live external provider.

There are no separate completed-task report files for Tasks 02–17 in this
repository. Their completion evidence is therefore the task documentation and
the feature-level tests named below.

## Functional acceptance-criteria traceability

| Requirement / criteria | Evidence | Status |
| --- | --- | --- |
| CA-01.1, CA-01.2, CA-01.3 | `test_administrator_creates_client_with_durable_pending_identity_provisioning`; `test_duplicate_email_is_rejected_for_inactive_account`; `test_client_validation_rejects_invalid_data_without_persisting` | Pass |
| CA-02.1, CA-02.2, CA-02.3 | `test_administrator_lists_searches_and_reads_client_detail`; `test_client_role_cannot_access_client_records`; `client-management.test.tsx` search flow | Pass |
| CA-03.1, CA-03.2, CA-03.3 | `test_administrator_updates_profile_and_state_with_persistence`; `test_deactivated_linked_account_is_rejected_as_unauthenticated`; client-management deactivation flow | Pass |
| CA-03.4 | Deferred outside the stated MVP with RF-22 biometrics, as explicitly recorded in RF-03/DEC-05. | Not applicable to this MVP verification |
| CA-04.1, CA-04.2, CA-04.3 | `test_protected_endpoint_returns_authenticated_active_identity`; `test_expired_or_invalid_session_is_rejected`; `test_protected_endpoint_rejects_absent_session`; `app.test.tsx` OIDC callback/sign-in flows | Pass |
| CA-05.1, CA-05.2, CA-05.3 | `test_client_is_denied_direct_administrative_api_access`; `test_administrator_can_access_administrative_api`; cross-client and `/clients` assertions in the new contract test | Pass |
| CA-09.1, CA-09.2, CA-09.3 | `test_unexpired_token_is_client_bound_and_passive_validation_does_not_consume`; `test_failed_delivery_is_persisted_as_failure_not_success`; `test_admin_api_issues_invitation_and_returns_controlled_delivery_failure`; client-management invitation flow | Pass |
| CA-10.1, CA-10.2, CA-10.3 | `test_access_api_passively_validates_and_only_explicit_redemption_consumes`; `test_expired_and_already_used_tokens_are_rejected`; `test_unexpired_token_is_client_bound_and_passive_validation_does_not_consume`; onboarding-access UI flows | Pass |
| CA-11.1, CA-11.2, CA-11.3 | `test_valid_physical_data_persists_and_invalid_values_are_rejected`; `test_completion_boundary_requires_all_fields_and_conditional_details`; `test_partial_draft_is_created_and_reloaded_without_sensitive_audit_values`; onboarding-form UI flows | Pass |
| CA-12.1, CA-12.2, CA-12.3 | `test_true_conditional_answers_require_nonblank_details`; `test_client_scope_isolation_and_ordinary_profile_models_do_not_contain_health_fields`; `test_client_can_access_only_own_draft_and_admin_is_denied` | Pass |
| CA-13.1, CA-13.2, CA-13.3 | `test_completion_requires_complete_own_draft_and_records_timestamp_atomically`; `test_requires_completed_authoritative_onboarding`; new contract test | Pass |
| CA-15.1, CA-15.2, CA-15.3 | `test_requires_completed_authoritative_onboarding`; `test_generates_only_client_scoped_proposal_using_completed_onboarding`; `test_client_generation_api_resolves_only_its_authenticated_identity` | Pass |
| CA-15.4, CA-15.5, CA-15.6 | `test_generates_only_client_scoped_proposal_using_completed_onboarding`; `test_reuses_the_single_active_draft_without_calling_the_provider_again`; `test_reuses_an_instructor_draft_without_calling_the_provider` | Pass |
| CA-16.1, CA-16.2, CA-16.3 | `test_current_plan_is_scoped_to_the_authenticated_client_and_survives_reload`; `test_client_without_current_plan_receives_an_empty_response`; `test_training_drafts_are_visible_only_to_the_owning_client`; current-training UI flows | Pass |
| CA-17.1, CA-17.2, CA-17.3, CA-17.4 | `test_initial_proposal_approval_activation_and_immutable_history`; `test_client_confirmed_adaptation_creates_one_new_current_version`; `test_current_plan_is_scoped_to_the_authenticated_client_and_survives_reload`; `test_client_cannot_have_two_proposals_even_with_different_origins` | Pass |
| CA-18.1, CA-18.2, CA-18.3 | `test_chat_is_client_scoped_persisted_and_never_mutates_plan`; `test_health_context_is_minimized_to_relevant_client_question`; new contract test; training-chat UI flows | Pass |
| CA-18.4, CA-18.5 | `test_retry_and_failure_leave_training_plan_unchanged`; new contract test; `test_chat_can_update_an_instructor_draft` | Pass |
| CA-19.1, CA-19.2, CA-19.3, CA-19.4 | `test_client_confirmed_adaptation_creates_one_new_current_version`; `test_supported_operation_types_are_persisted_without_catalog_mutation`; new contract test | Pass |

## EXT-RF-AI-01 traceability

| Criterion | Evidence | Status |
| --- | --- | --- |
| EXT-CA-AI-01.1 | `test_client_conversation_is_own_scoped_and_admin_cannot_read_raw_history`; onboarding-conversation UI flow | Pass |
| EXT-CA-AI-01.2 | `test_ready_turn_extracts_valid_data_without_completing`; onboarding-conversation structured-progress flow | Pass |
| EXT-CA-AI-01.3 | `test_invalid_final_extraction_preserves_existing_draft`; `test_completion_boundary_requires_all_fields_and_conditional_details` | Pass |
| EXT-CA-AI-01.4 | `test_normal_interview_turn_never_mutates_structured_draft_and_is_idempotent`; `test_partial_draft_is_created_and_reloaded_without_sensitive_audit_values`; retry/resume UI flow | Pass |
| EXT-CA-AI-01.5 | `test_completion_requires_complete_own_draft_and_records_timestamp_atomically`; `test_requires_completed_authoritative_onboarding`; new contract test | Pass |
| EXT-CA-AI-01.6 | `test_client_conversation_is_own_scoped_and_admin_cannot_read_raw_history`; `test_client_scope_isolation_and_ordinary_profile_models_do_not_contain_health_fields` | Pass |
| EXT-CA-AI-01.7 | `test_transient_interview_failure_retries_once`; `test_invalid_final_extraction_preserves_existing_draft`; provider-adapter controlled-failure tests | Pass |
| EXT-CA-AI-01.8 | `test_access_api_passively_validates_and_only_explicit_redemption_consumes`; onboarding-access and onboarding-form UI flows | Pass |

## Language, design, and responsive evidence

| Criterion | Evidence | Status |
| --- | --- | --- |
| EXT-CA-LANG-01.1 | The 39 passing frontend tests cover Portuguese validation, empty, authorization, onboarding, admin, training and chat states. Components use the shared Task 08/18 shell, MUI theme, `StatusNotice`, form controls, and navigation patterns. | Automated representative coverage passes; live visual audit remains below. |
| EXT-CA-LANG-01.2 | Controlled AI responses in onboarding, generation, chat, and adaptation tests are Portuguese; `training-chat-page.test.tsx` verifies a Portuguese client flow. Schema validation remains server-side. | Pass |
| EXT-CA-LANG-01.3 | `onboarding-form.test.tsx` verifies decimal-comma normalization; `onboarding-completion.tsx` formats completion timestamps with `Intl.DateTimeFormat('pt-BR')`. | Pass for presently displayed MVP formats |
| EXT-CA-LANG-01.4 | Static configuration inspection: `realm-academia.json` sets `supportedLocales` and `defaultLocale` to `pt-BR`; the repository-managed Keycloak `academia` login theme declares `locales=pt-BR`. | Configuration passes; hosted login/first-access rendering requires live browser confirmation. |
| EXT-CA-LANG-01.5 | `onboarding-conversation-page.test.tsx` identifies the conversation as mobile-friendly; the app, admin, current-training, onboarding, and chat UI suites pass using the shared visual system. | **Unverified live viewport audit** at 360×800, 768×1024, and 1366×768. |

## DEC-16 / RNF evidence

| Criteria | Result |
| --- | --- |
| CA-RNF01.1 | **Unverified.** The approved ten-run, approximately-50-client timing measurement and three-request burst were not executed in this run. Automated suites establish correctness only, not the two-second timing criterion. |
| CA-RNF01.2 | Partial automated evidence: UI loading/controlled-error states and adapter timeout/retry tests pass. **Unverified** visible-processing measurement within 200 ms in a real browser. |
| CA-RNF01.3 | Pass by controlled adapter-failure tests and the new AI-failure contract test; no indefinite external call is used in tests. |
| CA-RNF02.1, CA-RNF02.2 | Partial automated evidence from navigation/form UI suites and shared Task 08/18 components. **Unverified** intended-user checklist without source-code consultation. |
| CA-RNF02.3 | **Unverified.** Requires an intended client, instructor, and administrator session using the DEC-16 checklist. |
| CA-RNF03.1, CA-RNF03.2, CA-RNF03.3 | **Unverified.** The required live 360×800, 768×1024, and 1366×768 audits (including no smartphone horizontal scroll) were not run; no browser/E2E dependency was added because that would exceed this verification task's existing-tooling scope. |
| CA-RNF04.1, CA-RNF04.2, CA-RNF04.3 | Partial evidence: modular service/adapter contract tests and full backend/frontend regressions pass. Repository-wide Ruff is blocked by the three pre-existing migration-format findings noted above. |
| CA-RNF05.1 | **Unverified.** The required eight-hour local health-check soak was not run. |
| CA-RNF05.2, CA-RNF05.3 | Pass: controlled e-mail delivery failure tests, controlled AI failures, and independent current-plan availability in the new contract test. |
| CA-RNF06.1, CA-RNF06.2, CA-RNF06.3 | Pass: OpenAI/Ollama/provider-selection and controlled-adapter failure tests demonstrate the provider-neutral adapter boundary and controlled public behavior. |
| Restart recovery | **Unverified.** The required normal stack restart and five-minute data-preservation check was not run. |

## Remaining sign-off work

Formal DEC-16 MVP sign-off remains blocked only by the explicitly unverified
measurements above: the 50-client/timing and three-request burst measurement,
live browser viewport/accessibility audit, intended-user checklist, eight-hour
soak, and restart-recovery check. These are evidence gaps, not product defects.
The pre-existing backend migration lint findings should be corrected by their
own focused maintenance change before treating repository-wide lint as clean.
