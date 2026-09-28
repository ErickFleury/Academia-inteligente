# Production hardening implementation

User scope: add deployment security without changing gym workflows; leave the
facial pilot behavior unchanged. Approved Nginx as a free gateway, prepare MFA
without enforcing it, retain Keycloak 26.6.3. No host firewall or public deployment
is applied by this task. Existing development Compose remains available.

Requirements: RF-04/05, RF-09/10 delivery, RN-02/04/05/10/11/23/29/34,
RNF01–06, TEC-03/08/09 and section 6.1.1. Roles, enrollment, training approval,
biometrics and UI functionality retain their original acceptance criteria.

Checkpoints:
1. Non-root production backend, mounted secrets and authenticated TLS SMTP.
2. Standalone production Compose, HTTPS gateway, private services and identity
   deployment configuration. No Keycloak upgrade or mandatory MFA.
3. Firewall preparation, monitoring, backup/recovery documentation and tooling;
   integration and regression verification.

Checkpoint 1: 20 runtime/SMTP/invitation tests passed; Ruff checks/format passed.
The production image built and imported the application under UID 10001 with a
read-only filesystem, no capabilities and no pytest/Ruff installed. Local SMTP
continues to default to the existing unauthenticated Mailpit connection. TLS
options verify certificates and never fall back to sending credentials in clear.
Secret-file failures report variable names without secret contents.

Checkpoint 2: production gateway and Keycloak images built; Keycloak remains
26.6.3. Fresh isolated PostgreSQL and realm imports started successfully, with all
application migrations applied. The production backend, identity, database and
gateway became healthy. Rendered Compose configuration confirms that only the
gateway publishes ports in the default profile. Nginx configuration validation
passed under its unprivileged, read-only runtime.

HTTPS integration checks passed for SPA deep links, security headers, API
health/authorization, restricted identity administration (including spoofed
forwarding headers), hidden API documentation/identity health, body-size limits,
AI request throttling, fixed-host HTTP redirects and unknown-host rejection.
A synthetic administrator completed themed Keycloak login with S256 PKCE,
authenticated against the backend, revoked its refresh token, completed the logout
redirect and received `login_required` on a subsequent silent SSO attempt.
No OTP challenge or new business functionality was introduced. Production
preparation exposes optional Configure OTP with no default/user assignment.

All verification uses separate `academia-hardening-review` projects and synthetic
credentials under `/tmp`; no existing development accounts or volumes are reset.

Checkpoint 3: all 407 backend tests passed, including PostgreSQL integration
coverage. Thirteen deployment tests passed, covering private configuration,
input validation, optional MFA, provider compatibility, firewall plan boundaries,
backup integrity, restart-after-failure and empty-target restoration guards.
Ruff lint/format checks and Git whitespace checks passed. The frontend production
build completed as part of the gateway image; no frontend application code changed.

A maintenance backup stopped/restarted only the synthetic project's active
writers. Both application and identity dumps restored successfully into a second,
empty project; application migration version and identity subject hashes matched.
A second restore was rejected because the target was populated. Health checks
passed after restarting writers. A sensitive query/header canary was absent from
gateway logs. The test gateway listened only on loopback test ports 18080/18443.

Operational files: `docs/deployment/README.md`, `firewall-plan.py`, `operations.py`
and their tests. Firewall generation prints a review plan and changes nothing.
Monitoring exposes health checks/exit status, with no externally configured alert
channel. Backup output is private but not encrypted by the tool; encrypted storage
and off-host replication are required deployment inputs. Setup includes separate
production state, certificates, authenticated SMTP, private identity administration,
optional MFA activation, restore drills and rollback instructions.

Remaining rollout prerequisites: actual host/domain, trusted and automatically
renewed certificates, reviewed Docker-aware/provider firewall policy, isolated
SMTP relay and delivery validation, real optional provider keys, encrypted off-host
backups, alert routing and any existing-account migration. No public rollout,
real SMTP delivery, external firewall scan or production account migration was
performed. Keycloak remains intentionally unupgraded and the facial pilot retains
its previous limitations. These are explicit boundaries, not assurances that a
future Internet deployment is already protected against every attack.

Reversible code checkpoints: `69d6abe` (backend runtime/SMTP) and `f755fdf`
(production gateway/identity). The following operations/documentation commit
completes this task; none of these commits are pushed automatically.
