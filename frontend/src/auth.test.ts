import { afterEach, beforeEach, expect, test, vi } from 'vitest'

import { OidcSessionClient, sessionIdleTimeoutMs } from './auth'

beforeEach(() => sessionStorage.clear())
afterEach(() => vi.unstubAllGlobals())

function session(overrides: Record<string, unknown> = {}) {
  return {
    accessToken: 'access', refreshToken: 'refresh', expiresAt: Date.now() + 30_000,
    lastActivityAt: Date.now(), roles: ['client'], ...overrides,
  }
}

test('expires a local session after exactly five minutes without activity', () => {
  sessionStorage.setItem('academia.session', JSON.stringify(session({ lastActivityAt: Date.now() - sessionIdleTimeoutMs })))
  expect(new OidcSessionClient().getSession()).toBeNull()
})

test('renews an active session with its refresh token', async () => {
  sessionStorage.setItem('academia.session', JSON.stringify(session()))
  const fetchMock = vi.fn().mockResolvedValueOnce({
    ok: true,
    json: async () => ({ access_token: 'renewed-access', refresh_token: 'rotated-refresh', expires_in: 300 }),
  }).mockResolvedValueOnce({ ok: true, json: async () => ({ roles: ['client'] }) })
  vi.stubGlobal('fetch', fetchMock)
  const refreshed = await new OidcSessionClient().refreshSession()
  expect(refreshed?.accessToken).toBe('renewed-access')
  expect(refreshed?.roles).toEqual(['client'])
  expect(new URLSearchParams(fetchMock.mock.calls[0][1].body).get('grant_type')).toBe('refresh_token')
  expect(new URLSearchParams(fetchMock.mock.calls[0][1].body).get('refresh_token')).toBe('refresh')
})

test('uses active local roles instead of stale mixed token roles after renewal', async () => {
  sessionStorage.setItem('academia.session', JSON.stringify(session({ roles: ['client', 'instructor'] })))
  const token = `header.${btoa(JSON.stringify({ realm_access: { roles: ['client', 'instructor'] } }))}.signature`
  vi.stubGlobal('fetch', vi.fn()
    .mockResolvedValueOnce({ ok: true, json: async () => ({ access_token: token, refresh_token: 'new', expires_in: 300 }) })
    .mockResolvedValueOnce({ ok: true, json: async () => ({ roles: ['client'] }) }))
  expect((await new OidcSessionClient().refreshSession())?.roles).toEqual(['client'])
})

test('does not retain stale privileges when active-role verification fails', async () => {
  sessionStorage.setItem('academia.session', JSON.stringify(session()))
  vi.stubGlobal('fetch', vi.fn()
    .mockResolvedValueOnce({ ok: true, json: async () => ({ access_token: 'new', refresh_token: 'new', expires_in: 300 }) })
    .mockResolvedValueOnce({ ok: false, status: 401 }))
  expect(await new OidcSessionClient().refreshSession()).toBeNull()
  expect(sessionStorage.getItem('academia.session')).toBeNull()
})

test.each([['client'], ['employee', 'instructor']])('login stores only the locally active roles: %s', async (...roles) => {
  const previousUrl = window.location.href
  window.history.replaceState({}, '', '/?code=valid&state=state')
  sessionStorage.setItem('academia.pkce.verifier', 'verifier')
  sessionStorage.setItem('academia.oidc.state', 'state')
  const token = `header.${btoa(JSON.stringify({ realm_access: { roles: ['client', 'employee', 'instructor'] } }))}.signature`
  vi.stubGlobal('fetch', vi.fn()
    .mockResolvedValueOnce({ ok: true, json: async () => ({ access_token: token, refresh_token: 'new', expires_in: 300 }) })
    .mockResolvedValueOnce({ ok: true, json: async () => ({ roles }) }))
  const client = new OidcSessionClient()
  await client.completeLogin()
  expect(client.getSession()?.roles).toEqual(roles)
  window.history.replaceState({}, '', previousUrl)
})

test('clears a session when refresh fails', async () => {
  sessionStorage.setItem('academia.session', JSON.stringify(session()))
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: false }))
  expect(await new OidcSessionClient().refreshSession()).toBeNull()
  expect(sessionStorage.getItem('academia.session')).toBeNull()
})

function deferredResponse() {
  let resolve!: (response: unknown) => void
  const promise = new Promise((done) => { resolve = done })
  return { promise, resolve }
}

const renewedToken = { ok: true, json: async () => ({ access_token: 'renewed', refresh_token: 'rotated', expires_in: 300 }) }

test('deduplicates refreshes and cannot restore a session after logout', async () => {
  sessionStorage.setItem('academia.session', JSON.stringify(session()))
  const pending = deferredResponse()
  const fetchMock = vi.fn().mockReturnValueOnce(pending.promise)
    .mockResolvedValue({ ok: true, json: async () => ({ roles: ['client'] }) })
  vi.stubGlobal('fetch', fetchMock)
  const client = new OidcSessionClient()
  const first = client.refreshSession()
  expect(client.refreshSession()).toBe(first)
  expect(fetchMock).toHaveBeenCalledTimes(1)
  client.clearSession()
  pending.resolve(renewedToken)
  expect(await first).toBeNull()
  expect(client.getSession()).toBeNull()
})

test('a late refresh failure does not clear a newer session', async () => {
  sessionStorage.setItem('academia.session', JSON.stringify(session()))
  const pending = deferredResponse()
  vi.stubGlobal('fetch', vi.fn().mockReturnValue(pending.promise))
  const client = new OidcSessionClient()
  const refreshing = client.refreshSession()
  sessionStorage.setItem('academia.session', JSON.stringify(session({ accessToken: 'new-login' })))
  pending.resolve({ ok: false })
  await refreshing
  expect(client.getSession()?.accessToken).toBe('new-login')
})

test('preserves activity recorded while refresh is in flight', async () => {
  sessionStorage.setItem('academia.session', JSON.stringify(session({ lastActivityAt: Date.now() - 60_000 })))
  const pending = deferredResponse()
  vi.stubGlobal('fetch', vi.fn().mockReturnValueOnce(pending.promise)
    .mockResolvedValue({ ok: true, json: async () => ({ roles: ['client'] }) }))
  const client = new OidcSessionClient()
  const refreshing = client.refreshSession()
  const active = client.recordActivity()
  pending.resolve(renewedToken)
  expect((await refreshing)?.lastActivityAt).toBe(active?.lastActivityAt)
})

test.each([null, [], { access_token: 'a', refresh_token: 'r', expires_in: '300' }, { access_token: 'a', refresh_token: 'r', expires_in: -1 }])('rejects malformed refresh responses: %j', async (payload) => {
  sessionStorage.setItem('academia.session', JSON.stringify(session()))
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, json: async () => payload }))
  const client = new OidcSessionClient()
  expect(await client.refreshSession()).toBeNull()
  expect(client.getSession()).toBeNull()
})

test('requires a saved state and removes the authorization code even on failure', async () => {
  window.history.replaceState({}, '', '/?code=secret')
  sessionStorage.setItem('academia.pkce.verifier', 'verifier')
  const fetchMock = vi.fn()
  vi.stubGlobal('fetch', fetchMock)
  await expect(new OidcSessionClient().completeLogin()).rejects.toThrow('verify')
  expect(fetchMock).not.toHaveBeenCalled()
  expect(window.location.search).toBe('')
})

test('cancelling login during token exchange prevents session creation', async () => {
  window.history.replaceState({}, '', '/?code=secret&state=state')
  sessionStorage.setItem('academia.pkce.verifier', 'verifier')
  sessionStorage.setItem('academia.oidc.state', 'state')
  const pending = deferredResponse()
  vi.stubGlobal('fetch', vi.fn().mockReturnValueOnce(pending.promise)
    .mockResolvedValue({ ok: true, json: async () => ({ roles: ['client'] }) }))
  const client = new OidcSessionClient()
  const login = client.completeLogin()
  client.clearSession()
  pending.resolve(renewedToken)
  await expect(login).rejects.toThrow('cancelled')
  expect(client.getSession()).toBeNull()
})
