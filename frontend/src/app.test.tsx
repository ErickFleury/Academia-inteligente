import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, expect, test, vi } from 'vitest'

import { App } from './app'
import { OidcSessionClient } from './auth'

beforeEach(() => {
  window.history.replaceState({}, '', '/')
  sessionStorage.clear()
})

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

test('renders a sign-in action without a session', () => {
  render(<App />)

  expect(screen.getByRole('heading', { name: 'Academia Inteligente' })).toBeInTheDocument()
  expect(screen.getByRole('button', { name: 'Entrar' })).toBeInTheDocument()
})

test('shows an unauthenticated state for a protected route without a session', () => {
  window.history.replaceState({}, '', '/dashboard')

  render(<App />)

  expect(screen.getByText('Sessão necessária para acessar esta página.')).toBeInTheDocument()
})

test('stores a usable session after a valid OIDC callback', async () => {
  sessionStorage.setItem('academia.pkce.verifier', 'verifier')
  sessionStorage.setItem('academia.oidc.state', 'state')
  window.history.replaceState({}, '', '/dashboard?code=valid-code&state=state')
  vi.stubGlobal(
    'fetch',
    vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ access_token: 'access-token', expires_in: 300 }),
    }),
  )

  render(<App />)

  expect(await screen.findByText('Sessão autenticada.')).toBeInTheDocument()
  expect(new URLSearchParams(vi.mocked(fetch).mock.calls[0][1]?.body as string).get('redirect_uri')).toBe(
    'http://localhost:5173/',
  )
})

test('hides administrative navigation and denies the administrative page to a client', () => {
  sessionStorage.setItem(
    'academia.session',
    JSON.stringify({ accessToken: 'access-token', expiresAt: Date.now() + 300_000, roles: ['client'] }),
  )
  window.history.replaceState({}, '', '/admin')

  render(<App />)

  expect(screen.getByText('Você não tem permissão para acessar esta página.')).toBeInTheDocument()
  expect(screen.queryByRole('link', { name: 'Administração' })).not.toBeInTheDocument()
})

test('shows administrative navigation and page to an administrator', () => {
  sessionStorage.setItem(
    'academia.session',
    JSON.stringify({ accessToken: 'access-token', expiresAt: Date.now() + 300_000, roles: ['admin'] }),
  )
  window.history.replaceState({}, '', '/admin')
  vi.stubGlobal(
    'fetch',
    vi.fn().mockResolvedValue({ ok: true, json: async () => [] }),
  )

  render(<App />)

  expect(screen.getByRole('link', { name: 'Administração' })).toHaveAttribute('href', '/admin')
  expect(screen.getByRole('heading', { name: 'Clientes' })).toBeInTheDocument()
})

test('returns to the sign-in state when the client API rejects a stale session', async () => {
  sessionStorage.setItem(
    'academia.session',
    JSON.stringify({ accessToken: 'stale-token', expiresAt: Date.now() + 300_000, roles: ['admin'] }),
  )
  window.history.replaceState({}, '', '/admin')
  vi.stubGlobal(
    'fetch',
    vi.fn().mockResolvedValue({ ok: false, status: 401, json: async () => ({ detail: 'Unauthenticated' }) }),
  )

  render(<App />)

  expect(await screen.findByText('Sessão necessária para acessar esta página.')).toBeInTheDocument()
  expect(sessionStorage.getItem('academia.session')).toBeNull()
})

test('ends the provider session and clears the local session when signing out', () => {
  sessionStorage.setItem(
    'academia.session',
    JSON.stringify({
      accessToken: 'access-token',
      idToken: 'id-token',
      expiresAt: Date.now() + 300_000,
      roles: ['admin'],
    }),
  )
  const logoutUrl = new OidcSessionClient().endSession()

  expect(sessionStorage.getItem('academia.session')).toBeNull()
  expect(logoutUrl.href).toBe(
    'http://localhost:8080/realms/academia/protocol/openid-connect/logout?client_id=academia-web&post_logout_redirect_uri=http%3A%2F%2Flocalhost%3A5173%2F&id_token_hint=id-token',
  )
})
