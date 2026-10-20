# Academia Inteligente

The current local slice includes OIDC authentication, administrator-only client
registration/search, and Keycloak-provisioned client first access.

## Local runtime

1. Copy `.env.example` to `.env` and replace the local placeholder passwords.
   Set a distinct `KEYCLOAK_PROVISIONING_CLIENT_SECRET`; it belongs only to the
   backend-to-Keycloak service account.
2. Run `docker-compose up --build`.
3. Apply the application schema:

   ```bash
   docker-compose run --rm backend alembic upgrade head
   ```

4. Open the frontend at `http://localhost:5173`, API health at
   `http://localhost:8000/health`, API OpenAPI at `http://localhost:8000/docs`,
   Keycloak at `http://localhost:8080`, and Mailpit at `http://localhost:8025`.

The Keycloak login and first-access screens use the repository-managed
`academia` theme from `keycloak/themes/academia`. Docker Compose mounts it into
the Keycloak container and the managed realm selects it. Its `/opt/keycloak/data`
directory is backed by the `keycloak_data` Docker volume, preserving provisioned
identities and realm state across normal container recreation. After changing theme
resources, recreate Keycloak with
`docker compose up -d --force-recreate keycloak`; a pre-existing realm is not
overwritten by `--import-realm`, so set the realm's Login theme to `academia`
once in the local admin console or recreate the local Keycloak realm/volume if
you need its imported settings reapplied.

Use the `APP_ADMIN_USERNAME` and `APP_ADMIN_PASSWORD` values from `.env` to
sign in to the application. The bootstrap application administrator needs only
those credentials: Keycloak does not require an e-mail address, first name, or
last name for it. `KEYCLOAK_ADMIN` credentials are only for the Keycloak
administration console. The frontend origin must be listed in
`CORS_ALLOWED_ORIGINS` (the local default is `http://localhost:5173`).

When an administrator creates a client, the backend creates a Keycloak user
with only the `client` role and sends a Mailpit first-access message. Open the
message at `http://localhost:8025`, follow its Keycloak link, define the
client's password, and then sign in as that client. The password and action
token never enter PostgreSQL. A local client created before provisioning can be
selected under **Clientes** and retried with **Provisionar acesso**.

Clients reach pending onboarding after signing in; the admin panel no longer
requires an onboarding invitation. Existing secure invitation links remain valid
under their separate 24-hour policy.

For password recovery, open **Clientes → client details → Redefinir senha** as
an administrator, or **Meu perfil → settings cog → Redefinir senha** as the
client. On the login screen, use **Esqueceu sua senha?** and enter the registered
email. These flows send a Keycloak password-setup link valid for **15 minutes** to
the registered email. In local Docker, retrieve that email in Mailpit at
`http://localhost:8025`; it is not delivered to an external inbox. The password
changes only when the user completes Keycloak's form. Admin/profile requests
share a one-minute cooldown. Inactive/unlinked accounts or pending identity updates
must be resolved before sending from admin/profile actions. The Keycloak version
is unchanged. Existing installations need `alembic upgrade head` (migration
`20260927_31`) before restarting the backend.

Fresh realms include login recovery automatically. Existing local realms need
the targeted update below; it preserves users and other realm settings and uses
the running container's configured bootstrap administrator credentials:

```bash
docker compose exec -T keycloak bash -s < keycloak/enable-password-recovery.sh
```

For an existing production deployment, execute the same script in that
deployment's Keycloak container with its configured realm-administrator
credentials. It also supports the deployment's mounted administrator-password
secret. The script removes its temporary administrator session file on exit.

### Local facial-access pilot

The owner-only facial-access pilot runs through the local Docker `biometrics`
profile. New client/staff registrations now require successful webcam enrollment
or verified reuse of the same person's face. Administrators operate
`/admin/acesso-facial`; release is simulated and occupancy changes only after
explicit passage confirmation or a reasoned correction. See the
[pilot startup, recovery and owner checklist](docs/tasks/44-facial-pilot-verification.md).
Real webcam verification is still pending; no liveness or hardware readiness is claimed.

### Local conversational AI with Ollama

Local Ollama is the default for generation and embeddings. Existing `.env`
files retain their explicit provider choices; use these values for local operation:

```bash
AI_PROVIDER=ollama
OLLAMA_BASE_URL=http://ollama:11434
OLLAMA_MODEL=qwen3:8b
OLLAMA_TIMEOUT_SECONDS=120
AI_EMBEDDING_PROVIDER=ollama
AI_EMBEDDING_GPU_LAYERS=0
AI_EMBEDDING_MODEL=embeddinggemma
AI_EMBEDDING_DIMENSIONS=768
AI_ORCHESTRATION_ENABLED=false
```

Provision models once while connected, then start from cached artifacts:

```bash
docker compose up -d ollama
docker compose --profile provision-models run --rm ollama-model
docker compose --profile provision-models run --rm ollama-embedding-model
```

These explicit provisioning commands download models into `ollama_data`. Ordinary
startup does not execute model pulls. Recreate the backend after configuration
changes, then test `/assistente`. Stop/start inference with `docker compose stop
ollama` / `docker compose start ollama`; keep the model volume.

The Ollama API is accessible only to Compose services; this project does not
publish port 11434. To use an Ollama process installed directly on the Linux
host instead, set `OLLAMA_BASE_URL=http://host.docker.internal:11434`; the
Compose backend includes the required Linux host-gateway mapping.

The base service supports CPU execution and disables Ollama cloud features. For
GPU acceleration use `docker compose -f docker-compose.yml -f docker-compose.gpu.yml
up -d ollama`. This requires a working NVIDIA driver and Container Toolkit;
the project does not install drivers. Local quality and latency still require
verification on the deployment hardware.

OpenAI is optional and explicitly configured: set `AI_PROVIDER=openai` for
generation and/or `AI_EMBEDDING_PROVIDER=openai`,
`AI_EMBEDDING_MODEL=text-embedding-3-small`, `AI_EMBEDDING_DIMENSIONS=1536` for
embeddings, plus an `OPENAI_API_KEY`. There is no automatic hosted fallback.

The small embedding model uses system RAM by default, leaving GPU memory for
generation. `AI_EMBEDDING_GPU_LAYERS=-1` opts into automatic GPU offload; benchmark
before changing it on 8 GB cards. Structured agent calls reuse a 12K context
window when sufficient and grow it within `OLLAMA_CONTEXT_TOKENS` when needed.
Required restrictions are never truncated to fit. These are resource settings,
not a guarantee of laptop performance.

Administrators manage uploaded references at `/admin/referencias`: upload a
text-based PDF, Markdown or UTF-8 text document, inspect the extraction preview,
then explicitly activate its version. Replacing an active version is atomic;
changing embedding configuration requires reimporting and activating compatible
versions. Scanned PDFs need text extraction outside this initial workflow.
Clients inspect, edit and forget their compact facts at `/assistente/memoria`,
including while AI is unavailable. Existing transcript expiry still applies.

The pilot ceilings can be lowered through `AI_REFERENCE_MAX_ACTIVE_DOCUMENTS`
(100), `AI_REFERENCE_MAX_UPLOAD_MIB` (20), `AI_REFERENCE_MAX_PDF_PAGES` (500), and
`AI_REFERENCE_MAX_CHARACTERS` (2000000). Larger capacity needs separate validation.

Keep `AI_ORCHESTRATION_ENABLED=false` during deployment validation. After reviewing
the [pilot evidence](docs/ai-rag-evaluation.md), enable it with an explicit
comma-separated `AI_ORCHESTRATION_CLIENT_IDS` allowlist of local Client UUIDs.
Only a deliberate broader rollout should use `*`. Disabling the flag restores
existing conversational workflows and preserves reference data and memory controls.

For provisioned offline verification, add `-f docker-compose.offline.yml` after
the base Compose file and optional GPU override. It removes the paid credential,
forces local adapters, blocks outbound routing, disables ViaCEP and suppresses
external equipment images. Use local image uploads and manual address entry.
Keycloak and Mailpit run locally; internet inbox delivery is outside offline mode.
On Docker versions that do not publish ports for internal-only networks, exercise
the services inside that network using the documented verification scripts;
ordinary browser access requires a separately verified host ingress setup.
The override is a verification harness, not an offline installer.
Changing embedding configuration requires reindexing reference documents;
increment `AI_EMBEDDING_REVISION` when replacing a model artifact under the same
name. Query vectors are not persisted. The new orchestration path remains off
until its integrated verification is complete.

For a fresh local realm, `docker-compose up --build` imports the provisioning
service account and Mailpit SMTP configuration. Existing Keycloak realms are
not overwritten by Keycloak import; configure the same `academia-provisioner`
service account and SMTP settings through the Keycloak admin console before
using this flow.

Only the UI, API, Keycloak, and Mailpit are bound to loopback addresses.
PostgreSQL is available exclusively on the internal Compose network. For Internet
deployment, use the separate [production deployment guide](docs/deployment/README.md)
and `docker-compose.production.yml`. Only its HTTPS/redirect gateway is public;
Docker forwarding requires firewall rules in addition to UFW. Do not expose the
development stack directly.

## Quality checks

Run these commands through the containers so they use the approved baseline:

```bash
docker-compose run --rm backend ruff check .
docker-compose run --rm backend ruff format --check .
docker-compose run --rm backend pytest
docker-compose run --rm frontend npm run lint
docker-compose run --rm frontend npm run build
docker-compose run --rm frontend npm test
```

`docker-compose up --build` runs service health checks. To inspect them, use
`docker-compose ps`.

The frontend lockfile must be generated with the approved Node image before a
release build is used: `docker-compose run --rm frontend npm install`. This
foundation environment could not generate it because Docker daemon access was
unavailable during setup.
