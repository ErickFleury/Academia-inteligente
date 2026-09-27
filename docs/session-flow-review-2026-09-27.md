# Login, logout and redirect review

## Scope

User-requested review of all client, instructor and administrative sign-out
controls and login/logout redirects. Applies RF-04/05, section 2.2 session policy,
RN-02/04/05/23 and RNF01–04. RF-10 invitation routing is a necessary dependency:
a public invitation must not be redirected away by the generic login effect.
Existing role permissions, five-minute idle policy, PKCE, Keycloak-hosted
credentials and backend authorization remain authoritative. No dependency,
Keycloak version/configuration, backend, account or schema changes.

## Findings and fixes

- All three frontends already pass their sign-out action through the same
  application handler and shared button, including the mobile drawer. Retain
  those controls and their duplicate-click protection.
- Sign-out previously waited indefinitely for optional token revocation while
  protected content remained mounted. Now it clears storage and protected UI
  immediately; revocation is bounded to 1.5 seconds before navigating to the
  standard provider logout endpoint. Navigation failure offers a controlled
  retry retaining the ID-token hint. Provider navigation replaces history.
- Idle expiry or failed renewal could silently re-enter through an existing SSO
  cookie, or remain indefinitely on a redirect spinner after an earlier login
  callback. Termination now settles on the existing session-ended screen;
  explicit re-entry resets redirect guards and requests `prompt=login`.
- Callback errors/cancellation were ignored. Both code and error callbacks now
  clean their authentication URL parameters and offer controlled retry. PKCE
  state remains mandatory; a supplied response issuer must match the configured
  issuer. Completed/failed transactions clean their temporary state.
- Token exchange, role verification and renewal now bound network/body waiting
  to 15 seconds per request. An expired stored access token is renewed before
  protected screens appear; history restoration rechecks the local session.
- Requested application paths were lost because the configured OIDC callback
  is the root. Preserve only the local pathname in the PKCE transaction and
  restore it after success; reject external, protocol-relative, backslash,
  whitespace or query-bearing return targets. Existing role guards still apply.
  Query parameters (including invitation credentials) are never copied into
  this return-path storage. Root entry preserves client onboarding/feed and
  instructor defaults; administrators now reach the canonical `/admin` URL.
- Public invitation links were unintentionally subject to automatic login.
  They now keep their token-bound public flow. Moving from the public equipment
  catalog to a protected route correctly starts login.
- Client landing-page onboarding lookup failure left an endless preparation
  spinner. It now exposes retry using the existing lookup and destination rules.

The provider redirect follows the existing standard Keycloak endpoints, checked
against [Keycloak's OIDC endpoint documentation](https://www.keycloak.org/securing-apps/oidc-layers)
and [login options](https://www.keycloak.org/securing-apps/javascript-adapter).
No adapter migration or Keycloak upgrade is part of this work.

## Verification checkpoint

- 83 focused authentication/application tests passed (existing and new suites).
- TypeScript validation passed.
- New tests exercise desktop/mobile sign-out in all three areas, immediate
  credential removal, exactly one provider redirect, stalled/failed revocation,
  logout-return/Back behavior, navigation retry, five-minute idle termination,
  refresh after callback, expired-token startup, callback cancellation/state/
  issuer checks, bounded network/body/role requests, safe return paths,
  public invitations, public-to-protected navigation and role landing routes.
- Existing stale-session regression now verifies explicit re-entry rather than
  the former automatic SSO loop; permission checks were not relaxed.

Changed files: `frontend/src/auth.ts`, `app.tsx`, `browser-navigation.ts`,
`auth-redirects.test.ts`, `app-session.test.tsx`, `app.test.tsx`, and this report.
Final browser/regression/build evidence follows in the verification checkpoint.
