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
