export type Session = {
  accessToken: string
  expiresAt: number
}

const sessionKey = 'academia.session'
const verifierKey = 'academia.pkce.verifier'
const stateKey = 'academia.oidc.state'

function oidcConfig() {
  return {
    issuer: import.meta.env.VITE_OIDC_ISSUER,
    clientId: import.meta.env.VITE_OIDC_CLIENT_ID ?? 'academia-web',
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
      if (!session.accessToken || session.expiresAt <= Date.now()) {
        this.clearSession()
        return null
      }
      return session
    } catch {
      this.clearSession()
      return null
    }
  }

  async startLogin(): Promise<void> {
    const { issuer, clientId } = oidcConfig()
    const verifier = randomValue()
    const state = randomValue()
    sessionStorage.setItem(verifierKey, verifier)
    sessionStorage.setItem(stateKey, state)

    const authorizationUrl = new URL(`${issuer}/protocol/openid-connect/auth`)
    authorizationUrl.search = new URLSearchParams({
      client_id: clientId,
      redirect_uri: window.location.origin + window.location.pathname,
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

    const { issuer, clientId } = oidcConfig()
    const tokenResponse = await fetch(`${issuer}/protocol/openid-connect/token`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: new URLSearchParams({
        grant_type: 'authorization_code',
        client_id: clientId,
        code,
        redirect_uri: window.location.origin + window.location.pathname,
        code_verifier: verifier,
      }),
    })
    if (!tokenResponse.ok) throw new Error('Unable to start the authenticated session')

    const payload = (await tokenResponse.json()) as { access_token?: string; expires_in?: number }
    if (!payload.access_token || !payload.expires_in) throw new Error('Invalid authentication response')

    sessionStorage.setItem(
      sessionKey,
      JSON.stringify({ accessToken: payload.access_token, expiresAt: Date.now() + payload.expires_in * 1000 }),
    )
    sessionStorage.removeItem(verifierKey)
    sessionStorage.removeItem(stateKey)
    window.history.replaceState({}, '', currentUrl.pathname)
  }

  clearSession(): void {
    sessionStorage.removeItem(sessionKey)
    sessionStorage.removeItem(verifierKey)
    sessionStorage.removeItem(stateKey)
  }
}
