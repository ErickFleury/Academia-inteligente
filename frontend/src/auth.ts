export type Session = {
  accessToken: string
  expiresAt: number
  lastActivityAt: number
  roles: string[]
  idToken?: string
  refreshToken?: string
}

const sessionKey = 'academia.session'
const verifierKey = 'academia.pkce.verifier'
const stateKey = 'academia.oidc.state'
export const sessionIdleTimeoutMs = 5 * 60 * 1000

function oidcConfig() {
  return {
    issuer: import.meta.env.VITE_OIDC_ISSUER,
    clientId: import.meta.env.VITE_OIDC_CLIENT_ID ?? 'academia-web',
    redirectUri: import.meta.env.VITE_OIDC_REDIRECT_URI || 'http://localhost:5173/',
  }
}

function rolesFromAccessToken(accessToken: string): string[] {
  try {
    const payload = accessToken.split('.')[1]
    if (!payload) return []

    const decoded = JSON.parse(
      atob(payload.replaceAll('-', '+').replaceAll('_', '/')),
    ) as { realm_access?: { roles?: unknown } }
    const roles = decoded.realm_access?.roles
    return Array.isArray(roles) ? roles.filter((role): role is string => typeof role === 'string') : []
  } catch {
    return []
  }
}

function encodeBase64Url(bytes: Uint8Array): string {
  return btoa(String.fromCharCode(...bytes))
    .replaceAll('+', '-')
    .replaceAll('/', '_')
    .replaceAll('=', '')
}

function randomValue(): string {
  const bytes = new Uint8Array(32)
  crypto.getRandomValues(bytes)
  return encodeBase64Url(bytes)
}

async function sha256(value: string): Promise<string> {
  const digest = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(value))
  return encodeBase64Url(new Uint8Array(digest))
}

export class OidcSessionClient {
  getSession(): Session | null {
    const serialized = sessionStorage.getItem(sessionKey)
    if (!serialized) return null

    try {
      const session = JSON.parse(serialized) as Session
      if (
        !session.accessToken
        || !session.refreshToken
        || !session.lastActivityAt
        || session.lastActivityAt + sessionIdleTimeoutMs <= Date.now()
      ) {
        this.clearSession()
        return null
      }
      return {
        ...session,
        roles: Array.isArray(session.roles)
          ? session.roles.filter((role): role is string => typeof role === 'string')
          : [],
      }
    } catch {
      this.clearSession()
      return null
    }
  }

  recordActivity(): Session | null {
    const session = this.getSession()
    if (!session) return null
    const activeSession = { ...session, lastActivityAt: Date.now() }
    this.storeSession(activeSession)
    return activeSession
  }

  async refreshSession(): Promise<Session | null> {
    const session = this.getSession()
    if (!session?.refreshToken) return null

    const { issuer, clientId } = oidcConfig()
    let response: Response
    try {
      response = await fetch(`${issuer}/protocol/openid-connect/token`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: new URLSearchParams({
          grant_type: 'refresh_token',
          client_id: clientId,
          refresh_token: session.refreshToken,
        }),
      })
    } catch {
      this.clearSession()
      return null
    }
    if (!response.ok) {
      this.clearSession()
      return null
    }
    const payload = await this.tokenPayload(response)
    if (!payload.access_token || !payload.expires_in || !payload.refresh_token) {
      this.clearSession()
      return null
    }
    const refreshed = {
      accessToken: payload.access_token,
      expiresAt: Date.now() + payload.expires_in * 1000,
      lastActivityAt: session.lastActivityAt,
      roles: rolesFromAccessToken(payload.access_token),
      idToken: payload.id_token ?? session.idToken,
      refreshToken: payload.refresh_token,
    }
    this.storeSession(refreshed)
    return refreshed
  }

  async startLogin(): Promise<void> {
    const { issuer, clientId, redirectUri } = oidcConfig()
    const verifier = randomValue()
    const state = randomValue()
    sessionStorage.setItem(verifierKey, verifier)
    sessionStorage.setItem(stateKey, state)

    const authorizationUrl = new URL(`${issuer}/protocol/openid-connect/auth`)
    authorizationUrl.search = new URLSearchParams({
      client_id: clientId,
      redirect_uri: redirectUri,
      response_type: 'code',
      scope: 'openid profile',
      state,
      code_challenge: await sha256(verifier),
      code_challenge_method: 'S256',
    }).toString()
    window.location.assign(authorizationUrl)
  }

  async completeLogin(): Promise<void> {
    const currentUrl = new URL(window.location.href)
    const code = currentUrl.searchParams.get('code')
    if (!code) return

    const expectedState = sessionStorage.getItem(stateKey)
    const verifier = sessionStorage.getItem(verifierKey)
    if (!verifier || currentUrl.searchParams.get('state') !== expectedState) {
      throw new Error('Unable to verify the sign-in response')
    }

    const { issuer, clientId, redirectUri } = oidcConfig()
    const tokenResponse = await fetch(`${issuer}/protocol/openid-connect/token`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: new URLSearchParams({
        grant_type: 'authorization_code',
        client_id: clientId,
        code,
        redirect_uri: redirectUri,
        code_verifier: verifier,
      }),
    })
    if (!tokenResponse.ok) throw new Error('Unable to start the authenticated session')

    const payload = await this.tokenPayload(tokenResponse)
    if (!payload.access_token || !payload.expires_in || !payload.refresh_token) {
      throw new Error('Invalid authentication response')
    }
    this.storeSession({
      accessToken: payload.access_token,
      expiresAt: Date.now() + payload.expires_in * 1000,
      lastActivityAt: Date.now(),
      roles: rolesFromAccessToken(payload.access_token),
      idToken: payload.id_token,
      refreshToken: payload.refresh_token,
    })
    sessionStorage.removeItem(verifierKey)
    sessionStorage.removeItem(stateKey)
    window.history.replaceState({}, '', currentUrl.pathname)
  }

  clearSession(): void {
    sessionStorage.removeItem(sessionKey)
    sessionStorage.removeItem(verifierKey)
    sessionStorage.removeItem(stateKey)
  }

  endSession(): URL {
    const { issuer, clientId, redirectUri } = oidcConfig()
    const session = this.getSession()
    this.clearSession()

    const logoutParameters = new URLSearchParams({
      client_id: clientId,
      post_logout_redirect_uri: redirectUri,
    })
    if (session?.idToken) logoutParameters.set('id_token_hint', session.idToken)

    const logoutUrl = new URL(`${issuer}/protocol/openid-connect/logout`)
    logoutUrl.search = logoutParameters.toString()
    return logoutUrl
  }

  private storeSession(session: Session): void {
    sessionStorage.setItem(sessionKey, JSON.stringify(session))
  }

  private async tokenPayload(response: Response): Promise<{
    access_token?: string
    expires_in?: number
    id_token?: string
    refresh_token?: string
  }> {
    return response.json() as Promise<{
      access_token?: string
      expires_in?: number
      id_token?: string
      refresh_token?: string
    }>
  }
}
