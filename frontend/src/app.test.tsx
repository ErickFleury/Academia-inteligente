import { render, screen } from '@testing-library/react'
import { afterEach, beforeEach, expect, test, vi } from 'vitest'

import { App } from './app'

beforeEach(() => {
  window.history.replaceState({}, '', '/')
  sessionStorage.clear()
})

afterEach(() => vi.unstubAllGlobals())

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
})
