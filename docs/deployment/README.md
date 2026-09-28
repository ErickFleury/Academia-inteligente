# Production deployment and operations

This is a **separate deployment**, not an overlay for local development. It adds
Nginx 1.30.5, HTTPS, restricted ingress, private application/identity databases,
mounted credentials, bounded requests and recovery tooling. Keycloak stays at
26.6.3 as requested. Gym permissions, registration, training and facial pilot
rules are unchanged. Nothing here applies host firewall rules or deploys a server
automatically. See [implementation evidence](../production-hardening-2026-09-27.md).

## Prerequisites and scope

Use a Linux host with Docker Compose v2, a domain pointing at it, sufficient RAM
for PostgreSQL/Keycloak/application plus any optional providers, and recovery
console access. Choose the hosting provider, operator IP/CIDR, certificate issuer,
isolated SMTP relay and encrypted off-host backup destination before rollout.
The SMTP relay must support authenticated STARTTLS or implicit TLS; Mailpit is
not deployed. CA-06.4 still requires an isolated Docker SMTP service: arrange that
relay separately; this configuration does not waive the requirement or select
an email API instead. No vendor, billing account, certificate agent or alert destination
is created by these files.

Publish only TCP 80/443 through the gateway. Restrict SSH to the operator network.
Do not publish PostgreSQL, backend port 8000, Keycloak 8080/9000 or development
ports. Nginx restricts `/auth/admin` and the `master` realm to the operator CIDR;
ordinary application login remains public. Its allowlist uses the connection IP,
not a supplied forwarding header. If adding a CDN/load balancer later, review the
trusted proxy chain before changing this rule. The default gateway host binding
is IPv4; do not add IPv6 public bindings without corresponding provider/host rules.

The optional biometric stack remains the controlled local pilot, with its
existing limitations and loopback management port. This change does not certify
it for public biometric deployment. Keycloak security upgrades were explicitly
deferred; the gateway cannot fix vulnerabilities inside an older identity server.
This is a deployment baseline, not a WAF, volumetric DDoS service or security audit
certification.

## Prepare private configuration

Run from the repository root. Put real provider credentials in private files;
do not put secret values in command arguments, Git or shell history. For example,
substitute the domain, operator IP and SMTP settings below:

```bash
python3 docs/deployment/prepare.py \
  --domain gym.example.com \
  --admin-network 203.0.113.10/32 \
  --smtp-host smtp.example.com \
  --smtp-from gym@example.com \
  --smtp-username gym@example.com \
  --smtp-password-file /secure/inputs/smtp-password \
  --openai-key-file /secure/inputs/openai-key
```

Use `--smtp-security tls --smtp-port 465` for implicit TLS; STARTTLS/587 is the
default. `--compreface-key-file` is available when using the approved local pilot.
Omitted AI/face keys are placeholders, not functioning provider credentials.
Configure the existing provider before exercising its features; failures remain
controlled and do not bypass registration or training rules.

The script creates `.env.production` (0600) and `.deployment` (0700). It refuses
to overwrite either, so rerunning it cannot silently rotate database credentials.
Secret files are individually bind-mounted read-only and readable by their
non-root containers; their private parent prevents other host users from reading
them. Keep these directory permissions. Docker/root operators can access secrets.
Compose secrets on one host are files, not an encrypted secret manager.

The generated application administrator and identity bootstrap administrator have
separate random passwords in `secrets/app_admin_password` and
`secrets/keycloak_admin_password`. Retrieve them privately. Application username
is `admin` unless `--admin-username` is supplied; identity bootstrap username is
`identity-admin`. Establish a permanent identity operator and remove the temporary
bootstrap operator after validating recovery access. Do not delete the gym's
application administrator by mistake.

Install a real certificate and private key as:

- `.deployment/tls/fullchain.pem`
- `.deployment/tls/privkey.pem`

Keep the outer deployment directory 0700. The mounted `tls` directory needs 0755
and its files 0444 for the unprivileged gateway; do not move the key outside that
private parent with world-readable permissions. Obtain the initial certificate
using the chosen issuer's DNS or standalone method before starting the gateway.
HTTP-01 renewals can subsequently write into `.deployment/acme`: Nginx serves only
`/.well-known/acme-challenge/` there. No certificate issuance/renewal daemon is
installed. Configure a renewal timer, copy renewed files securely and reload:

```bash
docker compose --env-file .env.production -f docker-compose.production.yml exec -T gateway nginx -t
docker compose --env-file .env.production -f docker-compose.production.yml exec -T gateway nginx -s reload
```

Changing the domain requires rebuilding the frontend, updating its generated
Nginx configuration and editing Keycloak URLs through controlled administration;
restarting with a new environment value alone is insufficient.

## Start a new deployment

Apply the reviewed firewall/provider policy first, then:

```bash
docker compose --env-file .env.production -f docker-compose.production.yml config --quiet
docker compose --env-file .env.production -f docker-compose.production.yml build
docker compose --env-file .env.production -f docker-compose.production.yml up -d --wait postgres
docker compose --env-file .env.production -f docker-compose.production.yml run --rm migrate
docker compose --env-file .env.production -f docker-compose.production.yml up -d --wait gateway backend keycloak
python3 docs/deployment/operations.py health --url https://gym.example.com
```

Never combine this file with the development Compose file. The default project
is `academia-production`; use `-p` consistently if choosing another name. The
frontend is compiled into Nginx, with same-origin `/api` and `/auth` URLs. API
OpenAPI/docs endpoints are private; development access remains unchanged. Images
in remote URLs must work over HTTPS in the deployed browser.

Existing optional provider commands use the same profiles as development. Review
`.env.production` and the repository's local facial setup guide before enabling
`biometrics`; set `FACIAL_ACCESS_MODE=pilot` only in its approved environment and
provide its real key. Mandatory successful enrollment remains mandatory.
CompreFace management stays on loopback 8005, which conflicts with a development
instance using the same port on the same computer. Ollama retains its GPU/runtime
requirements and model setup; no model is automatically substituted. See
[local setup](../../README.md).

### Existing data is not migrated automatically

Production uses PostgreSQL for Keycloak, with separate least-privilege database
roles for identity and the application. Do not attach the development Keycloak
H2 volume, share its database volume, or import new random identities over existing
client records. Migrate an isolated copy first, preserving Keycloak user IDs and
local `Account.keycloak_subject` links. Verify client/instructor/admin access,
provisioning, invitations and logout before cutover. This task does not perform
that migration or reset any existing accounts.

Keycloak startup import only creates a missing realm. It does not reapply changes
to an existing realm. Editing the generated JSON therefore does not update a live
SMTP password, provisioning secret, redirect URI or MFA policy. Coordinate live
Keycloak changes with mounted application secrets, then recreate affected
containers. Rotate database passwords in PostgreSQL as well as their secret files;
changing files alone does not rotate initialized databases.

## MFA is prepared, not enforced

The production realm makes `CONFIGURE_TOTP` available with `defaultAction=false`.
No user receives that required action and the browser authentication flow is not
replaced. Existing password login steps remain unchanged. Do not enable a realm
wide default action or require OTP in the browser flow during this deployment.

When the owner later approves activation, first retain a tested recovery operator,
then use the restricted Keycloak Admin Console to assign **Configure OTP** to one
administrator in the correct realm. The gym administrator belongs to `academia`;
the identity operator belongs to `master`, whose policy must be managed separately.
Test enrollment, subsequent OTP login and recovery with that operator before
expanding. Remove/reset a lost OTP credential only through authorized identity
administration. No recovery codes or emergency bypass endpoints are introduced.
The [Keycloak administration guide](https://www.keycloak.org/docs/latest/server_admin/index.html)
describes per-user required actions and OTP configuration; check UI names against
the pinned version when performing that later operation.

## Firewall plan (never applied by the script)

```bash
python3 docs/deployment/firewall-plan.py \
  --interface eth0 --management-network 203.0.113.10/32 \
  > /tmp/academia-firewall-review.txt
```

Review the output and existing host/provider rules from a recovery console.
The plan supports Docker's **iptables backend**, including IPv6, and uses UFW for
host input plus `DOCKER-USER` for forwarded container traffic. **Stop if either
chain precheck fails.** Do not paste this plan onto a host using Docker's nftables
backend or lacking the IPv6 chain; adapt and validate its policy first. Repeat
interface-specific rules for every public interface, remove old broad allows,
and arrange persistence after Docker creates its chains. Apply only once: it is
an explicit review plan, not an idempotent firewall installer.

Docker-published ports can bypass UFW input rules; see
[Docker's firewall documentation](https://docs.docker.com/engine/network/packet-filtering-firewalls/).
Verify from another machine over IPv4 and any enabled IPv6 that only 80/443 and
operator-restricted SSH are reachable. Verify again after reboot. No such public
host test has been claimed for the local verification stack.

## Monitoring and log handling

```bash
python3 docs/deployment/operations.py health --url https://gym.example.com
openssl x509 -checkend 1209600 -noout -in .deployment/tls/fullchain.pem
```

The first command checks required container health, the API, TLS verification and
OIDC issuer metadata, returning nonzero on failure. `--ca-file` is only needed for
a private test CA. The second detects certificates expiring within 14 days. Run
these from a scheduler and route failure status to the chosen alert destination;
no external notifications or scheduler are configured here. Also monitor disk
space, container restarts, backup age and successful restore drills. Internal
Keycloak health/metrics are on port 9000 and must remain private.

Nginx logs only time, route category, status, duration and rate-limit status; it
omits IPs, query strings, IDs, headers and bodies. Normal backend HTTP access logs
and identity access logs are disabled. Container logs rotate at 10 MB × 3; Keycloak
authentication/admin audit events stay in its restricted database for seven days,
without admin request representations. Treat those records and diagnostic errors
as sensitive. Avoid debug logging in production. Audit monitoring still needs an
operator and alert policy; local retention is not a centralized monitoring service.

Limits are per connecting IP: general API 20 requests/sec with burst 80, identity
10/sec with burst 40, AI generation/chat 12/minute with burst 6, 40 concurrent
connections and a 10 MiB body cap. They preserve approved upload sizes and AI
timeouts. Shared gym NAT may require measured tuning. Excess traffic returns 429
with a retry header; oversized requests return 413. Keycloak temporarily delays
repeated failed logins rather than permanently locking users. These deliberate
abuse responses are the only intended changes to normal request handling.

## Backup and restoration

Backups contain credentials, private keys, identity, health and potentially
biometric data. **The tool does not encrypt them.** Use an encrypted filesystem
for the destination, encrypted off-host replication with restricted access and
an operator-defined retention policy. Do not place backups under Git or web roots.

Schedule a maintenance window; the command stops active writers briefly to keep
application and identity snapshots consistent, then restarts only those that were
running. Optional active CompreFace writers and database are included.

```bash
python3 docs/deployment/operations.py backup \
  --state-dir .deployment \
  --directory /encrypted-backups/academia-2026-09-27 \
  --maintenance
```

It saves PostgreSQL custom-format dumps, deployment configuration/secrets/TLS and
a SHA-256 manifest. A failed backup without a completed manifest is unusable.
The `finally` cleanup restarts writers on ordinary failures; after a host crash or
forced process termination, check and restart the previously running services
manually. Keep the corresponding Git commit/build metadata with each backup.
Checksums detect corruption, not an attacker replacing both the file and manifest.

Restore to a **different project and empty databases**. Use only trusted backup
archives. First verify the manifest with the helper, then extract configuration
into a new private directory (Python 3.13+):

```bash
python3 - <<'PY'
import os
import sys
import tarfile
from pathlib import Path
sys.path.insert(0, 'docs/deployment')
from operations import verify_backup
root, manifest = verify_backup('/encrypted-backups/academia-2026-09-27')
recovery = Path('/secure/academia-recovery')
os.umask(0o077)
recovery.mkdir(mode=0o700)  # Fails if already present; never overwrite live state.
with tarfile.open(root / 'configuration.tar.gz') as archive:
    archive.extractall(recovery, filter='data')
PY
```

Update the restored `env.production`'s `PRODUCTION_STATE_DIR` to that restored
`state` directory. Restore 0700 for state/secrets, 0600 for the env file, 0755 for
tls/acme and 0444 for mounted secret/certificate/nginx files; extraction can
restrict file modes. Create an empty `state/acme` directory. Preserve the restored
passwords and realm/provisioning secrets; do not run `prepare.py` to replace them.
On the same host choose different gateway ports or keep the recovered gateway
stopped until controlled cutover. Then:

```bash
docker compose --env-file /secure/academia-recovery/env.production \
  -f docker-compose.production.yml -p academia-recovery up -d --wait postgres
python3 docs/deployment/operations.py \
  --env-file /secure/academia-recovery/env.production --project academia-recovery \
  restore --directory /encrypted-backups/academia-2026-09-27 --empty-target
```

If the manifest includes biometrics, start only its empty database too, using the
biometrics profile, before restoration. Do not start application/identity/provider
writers or run migrations before importing. The tool rejects the source project,
nonempty databases and running writers. Configuration is restored separately so
it cannot overwrite live secrets. After importing, verify schema version and
matching credentials, start the matching code version in isolation and test all
roles before cutover. Never use `down -v` on a deployment you need to retain.

Rollback code/config using the focused Git checkpoints and matching images. When
a change includes database migrations, use its reviewed downgrade or a verified
backup; reverting source alone does not reverse database changes. This hardening
change introduces no application schema migration.

## Validation commands

```bash
docker compose run --rm --no-deps \
  -v "$PWD:/workspace:ro" backend \
  pytest -q -o cache_dir=/tmp/deployment-pytest /workspace/docs/deployment
docker compose run --rm --no-deps -e TEST_POSTGRES=1 \
  -e CORS_ALLOWED_ORIGINS=http://localhost:5173 backend pytest -q
```

The integration review used synthetic data, an isolated Compose project and a
short-lived local certificate. Real SMTP deliverability, public DNS/certificates,
provider firewall policy, off-host encryption and alert delivery require the
chosen deployment services and must be validated during rollout.
