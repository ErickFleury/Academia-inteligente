# Local LAN startup and RAG test controls

Date: 2026-10-20. Requested operation: start necessary services and explain
per-client RAG enablement. This is deployment work for the existing approved
stack and assistant amendment, not a new feature or broad pilot acceptance.
The clean tracked baseline was `6be4fb7`; the pre-existing audio file is excluded.

## Runtime changes

- Updated ignored local settings from the previous LAN address to `192.168.1.14`.
  Persisted the base/LAN-HTTPS/GPU Compose file selection and existing biometrics
  profile, retaining the current facial-access pilot.
- Added configurable `KEYCLOAK_HTTP_PORT` with the unchanged default of 8080.
  This deployment uses 18080 because ClipCascade occupies 8080. Internal
  Keycloak communication remains on 8080; public HTTPS remains on 8443.
- Generated a persistent local HTTPS certificate under ignored
  `.deployment/lan-certificates`, with SANs for the current LAN IP, localhost and
  loopback. Browsers/devices must trust this local certificate. No system trust
  store was modified.
- Backed up the existing `.env`, application database and Keycloak public-client
  configuration under private `.deployment/lan-start-20261020`. Validated the
  PostgreSQL custom-format dump before applying migrations 32–35 to the existing
  application database. No database reset or identity recreation occurred.
- Added the current frontend redirect, logout and web origin to the existing
  Keycloak client while preserving prior client settings and users.
- Started frontend, backend, PostgreSQL, Keycloak, Mailpit, GPU-enabled Ollama,
  and the five existing CompreFace services. Cached qwen3:8b and embeddinggemma
  are available. Generation and embedding adapters are explicitly local.
- Replaced the CompreFace UI health probe's absent `wget` executable with its
  already installed `curl`, including the matching production-provider definition.
- Kept orchestration disabled and the Client allowlist empty. The README now
  documents activation for a selected Client UUID, backend recreation with the
  same Compose configuration, and disabling the test again.

## Endpoints at verification time

| Service | Endpoint |
| --- | --- |
| Application | `https://192.168.1.14:5173` |
| Reference management | `https://192.168.1.14:5173/admin/referencias` |
| Keycloak | `https://192.168.1.14:8443` |
| API | `http://192.168.1.14:8000`; browser uses frontend `/api` proxy |
| Mailpit inbox | `http://localhost:8025`, host only |
| CompreFace management UI | `http://localhost:8005`, host only |
| PostgreSQL / Ollama / SMTP / biometric internals | Docker networks only |

These addresses depend on the host's DHCP lease. The prior isolated evaluation
stack remains stopped; this operation started the actual application stack.

## Verification and remaining limits

- Real HTTPS frontend delivery and API proxy requests passed using certificate
  validation, with no global TLS-verification bypass.
- Real administrator authorization-code/PKCE login and authenticated reference
  management passed. Credentials/tokens were not printed or committed.
- Authenticated biometric provider status reported available, with no pending
  cleanup. The management UI returned HTTP 200.
- Application database revision is `20261019_35`.
- Both AI adapters report `ollama`; orchestration reports `false` with an empty
  allowlist. Provisioning jobs are intentionally not persistent services.
- All 13 existing deployment configuration/operations tests passed after the
  configuration changes; Compose validation and Git whitespace checks passed.

Checks originated on the host using its LAN address; another device's browser
and certificate trust were not exercised. The earlier grounding, CPU-only and
laptop acceptance limits remain recorded in `docs/ai-rag-evaluation.md`. Enabling
a test client is an explicit pilot action, not a claim that those gates passed.
