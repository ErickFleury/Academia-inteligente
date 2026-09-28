import { webcrypto } from 'node:crypto'
import { afterEach, beforeEach, expect, test, vi } from 'vitest'
import { OidcSessionClient } from './auth'
import { replaceLocation } from './browser-navigation'

vi.mock('./browser-navigation', () => ({ replaceLocation: vi.fn() }))
beforeEach(() => {
  sessionStorage.clear()
  window.history.replaceState({}, '', '/')
  vi.stubGlobal('crypto', webcrypto)
  vi.stubEnv('VITE_OIDC_ISSUER', 'http://localhost:8080/realms/academia')
  vi.stubEnv('VITE_OIDC_REDIRECT_URI', 'http://localhost:5173/')
})
afterEach(() => { vi.useRealTimers(); vi.unstubAllGlobals(); vi.unstubAllEnvs(); vi.clearAllMocks() })
const token = { ok: true, json: async () => ({ access_token: 'access', refresh_token: 'refresh', id_token: 'id', expires_in: 300 }) }
function callback(path = '/instrutor/meus-planos') {
  sessionStorage.setItem('academia.oidc.state', 'state')
  sessionStorage.setItem('academia.pkce.verifier', 'verifier')
  sessionStorage.setItem('academia.login-return-path', path)
  window.history.replaceState({}, '', '/?code=one-use-code&state=state')
}
function storedSession() {
  sessionStorage.setItem('academia.session', JSON.stringify({ accessToken: 'access', refreshToken: 'refresh', idToken: 'id', roles: ['client'], expiresAt: Date.now() + 300_000, lastActivityAt: Date.now() }))
}

test('starts PKCE login with a fixed callback, remembers only the local path and replaces history', async () => {
  window.history.replaceState({}, '', '/instrutor/meus-planos?filter=mine#selection')
  await new OidcSessionClient().startLogin()
  const url = vi.mocked(replaceLocation).mock.calls[0][0]
  expect(url.pathname).toBe('/realms/academia/protocol/openid-connect/auth')
  expect(url.searchParams.get('redirect_uri')).toBe('http://localhost:5173/')
  expect(url.searchParams.get('code_challenge_method')).toBe('S256')
  expect(url.searchParams.get('code_challenge')).toMatch(/^[\w-]{43}$/)
  expect(url.searchParams.get('state')).toBe(sessionStorage.getItem('academia.oidc.state'))
  expect(sessionStorage.getItem('academia.login-return-path')).toBe('/instrutor/meus-planos')
})

test('a terminated session requires explicit credential entry instead of silent SSO', async () => {
  const client = new OidcSessionClient()
  client.clearSession()
  expect(client.hasLoggedOut()).toBe(true)
  client.beginLoginAfterLogout()
  await client.startLogin()
  expect(vi.mocked(replaceLocation).mock.calls[0][0].searchParams.get('prompt')).toBe('login')
})

test.each(['/admin/acesso-facial', '/instrutor/meus-planos', '/treino'])('restores %s after a valid callback and clears transient auth state', async (path) => {
  callback(path)
  sessionStorage.setItem('academia.logged-out', 'true')
  vi.stubGlobal('fetch', vi.fn().mockResolvedValueOnce(token).mockResolvedValue({ ok: true, json: async () => ({ roles: ['client'] }) }))
  expect(await new OidcSessionClient().completeLogin()).toBe(path)
  expect(window.location.search).toBe('')
  for (const key of ['academia.pkce.verifier', 'academia.oidc.state', 'academia.login-return-path', 'academia.logged-out']) expect(sessionStorage.getItem(key)).toBeNull()
})

test.each(['https://other.example/path', '//other.example', '/\\other.example', '/?code=sensitive'])('does not redirect to unsafe saved return path %s', async (path) => {
  callback(path)
  vi.stubGlobal('fetch', vi.fn().mockResolvedValueOnce(token).mockResolvedValue({ ok: true, json: async () => ({ roles: [] }) }))
  expect(await new OidcSessionClient().completeLogin()).toBe('/')
})

test.each(['error=access_denied&error_description=cancelled&state=state', 'code=one-use-code&state=wrong', 'code=one-use-code&state=state&iss=https://other.example'])('rejects invalid or cancelled callbacks and removes their URL parameters: %s', async (query) => {
  callback()
  window.history.replaceState({}, '', '/?' + query)
  const fetchMock = vi.fn()
  vi.stubGlobal('fetch', fetchMock)
  await expect(new OidcSessionClient().completeLogin()).rejects.toThrow()
  expect(fetchMock).not.toHaveBeenCalled()
  expect(window.location.search).toBe('')
  expect(sessionStorage.getItem('academia.oidc.state')).toBeNull()
  expect(sessionStorage.getItem('academia.session')).toBeNull()
})

test('stalled revocation cannot prevent provider logout and local credentials disappear immediately', async () => {
  vi.useFakeTimers()
  storedSession()
  const fetchMock = vi.fn(() => new Promise<Response>(() => {}))
  vi.stubGlobal('fetch', fetchMock)
  const client = new OidcSessionClient()
  const logout = client.endSession()
  expect(sessionStorage.getItem('academia.session')).toBeNull()
  await vi.advanceTimersByTimeAsync(1_500)
  const url = await logout
  expect(url.pathname).toBe('/realms/academia/protocol/openid-connect/logout')
  expect(url.searchParams.get('id_token_hint')).toBe('id')
  expect(url.searchParams.get('post_logout_redirect_uri')).toBe('http://localhost:5173/')
  expect(vi.mocked(fetch).mock.calls[0][1]?.signal?.aborted).toBe(true)
})

test('failed revocation still yields a provider logout URL', async () => {
  storedSession()
  vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('Network unavailable')))
  expect((await new OidcSessionClient().endSession()).searchParams.get('id_token_hint')).toBe('id')
})

test.each(['network', 'body', 'roles'])('stalled login %s has a bounded failure and clears the transaction', async (stage) => {
  vi.useFakeTimers()
  callback()
  const pending = new Promise<Response>(() => {})
  vi.stubGlobal('fetch', stage === 'roles'
    ? vi.fn().mockResolvedValueOnce(token).mockReturnValue(pending)
    : vi.fn().mockReturnValue(stage === 'body' ? Promise.resolve({ ok: true, json: () => pending }) : pending))
  const failure = expect(new OidcSessionClient().completeLogin()).rejects.toThrow('timed out')
  await vi.advanceTimersByTimeAsync(15_001)
  await failure
  expect(sessionStorage.getItem('academia.session')).toBeNull()
  expect(sessionStorage.getItem('academia.oidc.state')).toBeNull()
})

test('stalled refresh ends the local session and cannot silently return to SSO', async () => {
  vi.useFakeTimers()
  storedSession()
  vi.stubGlobal('fetch', vi.fn(() => new Promise<Response>(() => {})))
  const client = new OidcSessionClient()
  const refresh = client.refreshSession()
  await vi.advanceTimersByTimeAsync(15_000)
  expect(await refresh).toBeNull()
  expect(client.hasLoggedOut()).toBe(true)
})
