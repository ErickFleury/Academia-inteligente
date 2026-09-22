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
  const fetchMock = vi.fn().mockResolvedValue({
    ok: true,
    json: async () => ({ access_token: 'renewed-access', refresh_token: 'rotated-refresh', expires_in: 300 }),
  })
  vi.stubGlobal('fetch', fetchMock)
  const refreshed = await new OidcSessionClient().refreshSession()
  expect(refreshed?.accessToken).toBe('renewed-access')
  expect(new URLSearchParams(fetchMock.mock.calls[0][1].body).get('grant_type')).toBe('refresh_token')
  expect(new URLSearchParams(fetchMock.mock.calls[0][1].body).get('refresh_token')).toBe('refresh')
})

test('clears a session when refresh fails', async () => {
  sessionStorage.setItem('academia.session', JSON.stringify(session()))
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: false }))
  expect(await new OidcSessionClient().refreshSession()).toBeNull()
  expect(sessionStorage.getItem('academia.session')).toBeNull()
})
