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
