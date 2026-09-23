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

For onboarding, select a provisioned active client under **Clientes** and use
**Enviar convite de onboarding**. The SMTP message appears in Mailpit and the
link expires after 24 hours. A newer invitation invalidates unused prior links.
The link is validated/redeemed by the later secure-onboarding flow; opening it
must not consume it by itself.

### Local conversational AI with Ollama

OpenAI remains the initial configured provider. For local development without
an API cost, use the optional internal Ollama Compose profile. Set the following
values in `.env` (a smaller compatible model such as `qwen3:4b` can be used
instead):

```bash
AI_PROVIDER=ollama
OLLAMA_BASE_URL=http://ollama:11434
OLLAMA_MODEL=qwen3:8b
OLLAMA_TIMEOUT_SECONDS=30
```

Start it when needed:

```bash
docker compose --profile ollama up -d
```

The first execution downloads the configured model. It is then retained in the
`ollama_data` Docker volume. Recreate the backend with
`docker compose up --build -d backend`, then sign in as a client and test
`/onboarding/conversa`. To stop local inference without deleting the model,
run `docker compose --profile ollama stop ollama`; start it again with
`docker compose --profile ollama start ollama`.

The Ollama API is accessible only to Compose services; this project does not
publish port 11434. To use an Ollama process installed directly on the Linux
host instead, set `OLLAMA_BASE_URL=http://host.docker.internal:11434`; the
Compose backend includes the required Linux host-gateway mapping.

The optional Compose service requests every available NVIDIA GPU. The host must
have a compatible NVIDIA driver and NVIDIA Container Toolkit configured for
Docker; otherwise Ollama uses CPU or cannot start with GPU access. This project
does not configure a host GPU driver or expose GPU services publicly.

For a fresh local realm, `docker-compose up --build` imports the provisioning
service account and Mailpit SMTP configuration. Existing Keycloak realms are
not overwritten by Keycloak import; configure the same `academia-provisioner`
service account and SMTP settings through the Keycloak admin console before
using this flow.

Only the UI, API, Keycloak, and Mailpit are bound to loopback addresses.
PostgreSQL is available exclusively on the internal Compose network. Configure
UFW on the Linux host to permit only the intended public reverse-proxy/UI/API
ports; never publish PostgreSQL.

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
