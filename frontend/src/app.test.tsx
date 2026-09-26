import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, expect, test, vi } from 'vitest'

import { App } from './app'
import { OidcSessionClient } from './auth'

beforeEach(() => {
  window.history.replaceState({}, '', '/')
  sessionStorage.clear()
})

afterEach(() => {
  cleanup()
  vi.restoreAllMocks()
  vi.unstubAllGlobals()
})

test('redirects an unauthenticated visitor directly to Keycloak login', async () => {
  const startLogin = vi.spyOn(OidcSessionClient.prototype, 'startLogin').mockResolvedValue()
  render(<App />)

  expect(screen.getByRole('heading', { name: 'Academia Inteligente' })).toBeInTheDocument()
  expect(await screen.findByText('Redirecionando para o login')).toBeInTheDocument()
  expect(startLogin).toHaveBeenCalledOnce()
})

test('redirects an unauthenticated protected route directly to Keycloak login', async () => {
  const startLogin = vi.spyOn(OidcSessionClient.prototype, 'startLogin').mockResolvedValue()
  window.history.replaceState({}, '', '/dashboard')

  render(<App />)

  expect(await screen.findByText('Redirecionando para o login')).toBeInTheDocument()
  expect(startLogin).toHaveBeenCalledOnce()
})

test('shows the public equipment catalog without requiring a login', async () => {
  const startLogin = vi.spyOn(OidcSessionClient.prototype, 'startLogin').mockResolvedValue()
  window.history.replaceState({}, '', '/equipamentos')
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, json: async () => [] }))

  render(<App />)

  expect(await screen.findByRole('heading', { name: 'Conheça nossos equipamentos' })).toBeInTheDocument()
  expect(startLogin).not.toHaveBeenCalled()
})

test('shows client navigation when an authenticated client opens the equipment catalog', async () => {
  sessionStorage.setItem(
    'academia.session',
    JSON.stringify({ accessToken: 'access-token', refreshToken: 'refresh-token', expiresAt: Date.now() + 300_000, lastActivityAt: Date.now(), roles: ['client'] }),
  )
  window.history.replaceState({}, '', '/equipamentos')
  vi.stubGlobal('fetch', vi.fn((url: string) => {
    if (url.endsWith('/onboarding/me')) return Promise.resolve({ ok: true, json: async () => ({ status: 'completed' }) })
    return Promise.resolve({ ok: true, json: async () => [] })
  }))

  render(<App />)

  expect(await screen.findByRole('heading', { name: 'Conheça nossos equipamentos' })).toBeInTheDocument()
  expect(screen.getByRole('navigation', { name: 'Navegação da área do cliente' })).toBeInTheDocument()
  expect(screen.getByRole('link', { name: 'Equipamentos' })).toHaveAttribute('aria-current', 'page')
})

test('stores a usable session after a valid OIDC callback', async () => {
  sessionStorage.setItem('academia.pkce.verifier', 'verifier')
  sessionStorage.setItem('academia.oidc.state', 'state')
  window.history.replaceState({}, '', '/dashboard?code=valid-code&state=state')
  vi.stubGlobal(
    'fetch',
    vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ access_token: 'access-token', refresh_token: 'refresh-token', expires_in: 300 }),
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
    JSON.stringify({ accessToken: 'access-token', refreshToken: 'refresh-token', expiresAt: Date.now() + 300_000, lastActivityAt: Date.now(), roles: ['client'] }),
  )
  window.history.replaceState({}, '', '/admin')

  render(<App />)

  expect(screen.getByText('Você não tem permissão para acessar esta página.')).toBeInTheDocument()
  expect(screen.queryByRole('link', { name: 'Administração' })).not.toBeInTheDocument()
})

test('opens the own onboarding form only for an authenticated client', async () => {
  sessionStorage.setItem(
    'academia.session',
    JSON.stringify({ accessToken: 'access-token', refreshToken: 'refresh-token', expiresAt: Date.now() + 300_000, lastActivityAt: Date.now(), roles: ['client'] }),
  )
  window.history.replaceState({}, '', '/onboarding')
  vi.stubGlobal(
    'fetch',
    vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        status: 'draft',
        training_goal: null,
        training_experience: null,
        height_cm: null,
        weight_kg: null,
        has_limitations_or_complaints: null,
        limitations_or_complaints: null,
        uses_medications: null,
        medications: null,
        has_health_conditions: null,
        health_conditions: null,
      }),
    }),
  )

  render(<App />)

  expect(await screen.findByRole('heading', { name: 'Conte um pouco sobre você' })).toBeInTheDocument()
  expect(screen.getByRole('link', { name: 'Responder por conversa' })).toHaveAttribute('href', '/assistente')
})

test('uses the Assistente route for guided onboarding until completion', async () => {
  sessionStorage.setItem(
    'academia.session',
    JSON.stringify({ accessToken: 'access-token', refreshToken: 'refresh-token', expiresAt: Date.now() + 300_000, lastActivityAt: Date.now(), roles: ['client'] }),
  )
  window.history.replaceState({}, '', '/assistente')
  const fetchMock = vi.fn((url: string) => {
    if (url.endsWith('/onboarding/me')) return Promise.resolve({ ok: true, json: async () => ({ status: 'draft', completed_at: null }) })
    if (url.endsWith('/onboarding/conversation')) return Promise.resolve({ ok: true, json: async () => ({ messages: [], missing_required_fields: ['training_goal'], completion_ready: false }) })
    return Promise.resolve({ ok: true, json: async () => [] })
  })
  vi.stubGlobal('fetch', fetchMock)

  render(<App />)

  expect(await screen.findByRole('heading', { name: 'Vamos montar seu perfil de treino' })).toBeInTheDocument()
  expect(fetchMock.mock.calls.some(([url]) => String(url).includes('/training/chat'))).toBe(false)
})

test('uses the Assistente route for training chat after onboarding completion', async () => {
  sessionStorage.setItem(
    'academia.session',
    JSON.stringify({ accessToken: 'access-token', refreshToken: 'refresh-token', expiresAt: Date.now() + 300_000, lastActivityAt: Date.now(), roles: ['client'] }),
  )
  window.history.replaceState({}, '', '/assistente')
  vi.stubGlobal('fetch', vi.fn((url: string) => {
    if (url.endsWith('/onboarding/me')) return Promise.resolve({ ok: true, json: async () => ({ status: 'completed' }) })
    if (url.endsWith('/training/chat')) return Promise.resolve({ ok: true, json: async () => ({ messages: [] }) })
    if (url.endsWith('/training/adaptations')) return Promise.resolve({ ok: true, json: async () => [] })
    if (url.endsWith('/training/current')) return Promise.resolve({ ok: true, json: async () => ({ plan: null }) })
    return Promise.resolve({ ok: true, json: async () => [] })
  }))

  render(<App />)

  expect(await screen.findByRole('heading', { name: 'Como posso ajudar hoje?' })).toBeInTheDocument()
})

test('redirects the former onboarding conversation route to Assistente', async () => {
  sessionStorage.setItem(
    'academia.session',
    JSON.stringify({ accessToken: 'access-token', refreshToken: 'refresh-token', expiresAt: Date.now() + 300_000, lastActivityAt: Date.now(), roles: ['client'] }),
  )
  window.history.replaceState({}, '', '/onboarding/conversa')
  vi.stubGlobal('fetch', vi.fn((url: string) => {
    if (url.endsWith('/onboarding/me')) return Promise.resolve({ ok: true, json: async () => ({ status: 'draft', completed_at: null }) })
    if (url.endsWith('/onboarding/conversation')) return Promise.resolve({ ok: true, json: async () => ({ messages: [], missing_required_fields: ['training_goal'], completion_ready: false }) })
    return Promise.resolve({ ok: true, json: async () => [] })
  }))

  render(<App />)

  expect(await screen.findByRole('heading', { name: 'Vamos montar seu perfil de treino' })).toBeInTheDocument()
  expect(window.location.pathname).toBe('/assistente')
})

test('opens the current training page only for an authenticated client', async () => {
  sessionStorage.setItem(
    'academia.session',
    JSON.stringify({ accessToken: 'access-token', refreshToken: 'refresh-token', expiresAt: Date.now() + 300_000, lastActivityAt: Date.now(), roles: ['client'] }),
  )
  window.history.replaceState({}, '', '/treino')
  vi.stubGlobal('fetch', vi.fn()
    .mockResolvedValueOnce({ ok: true, json: async () => ({ plan: null }) })
    .mockResolvedValueOnce({ ok: true, json: async () => [] }))

  render(<App />)

  expect(await screen.findByRole('heading', { name: 'Meu treino' })).toBeInTheDocument()
  expect(screen.getByText('Seu treino ainda não está disponível')).toBeInTheDocument()
})

test('does not show onboarding form navigation after the client completes onboarding', async () => {
  sessionStorage.setItem(
    'academia.session',
    JSON.stringify({ accessToken: 'access-token', refreshToken: 'refresh-token', expiresAt: Date.now() + 300_000, lastActivityAt: Date.now(), roles: ['client'] }),
  )
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, json: async () => ({ status: 'completed' }) }))

  render(<App />)

  await vi.waitFor(() => expect(screen.queryByRole('link', { name: 'Onboarding' })).not.toBeInTheDocument())
  expect(screen.queryByRole('link', { name: 'Preencher onboarding' })).not.toBeInTheDocument()
})

test('keeps onboarding navigation hidden on client routes after onboarding completion', async () => {
  sessionStorage.setItem(
    'academia.session',
    JSON.stringify({ accessToken: 'access-token', refreshToken: 'refresh-token', expiresAt: Date.now() + 300_000, lastActivityAt: Date.now(), roles: ['client'] }),
  )
  window.history.replaceState({}, '', '/treino')
  vi.stubGlobal('fetch', vi.fn((url: string) => {
    if (url.endsWith('/onboarding/me')) {
      return Promise.resolve({ ok: true, json: async () => ({ status: 'completed' }) })
    }
    if (url.endsWith('/training/current')) {
      return Promise.resolve({ ok: true, json: async () => ({ plan: null }) })
    }
    return Promise.resolve({ ok: true, json: async () => [] })
  }))

  render(<App />)

  expect(await screen.findByRole('heading', { name: 'Meu treino' })).toBeInTheDocument()
  await vi.waitFor(() => expect(screen.queryByRole('link', { name: 'Onboarding' })).not.toBeInTheDocument())
})

test('shows onboarding form navigation for a client with a draft', async () => {
  sessionStorage.setItem(
    'academia.session',
    JSON.stringify({ accessToken: 'access-token', refreshToken: 'refresh-token', expiresAt: Date.now() + 300_000, lastActivityAt: Date.now(), roles: ['client'] }),
  )
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, json: async () => ({ status: 'draft' }) }))

  render(<App />)

  expect(await screen.findByRole('link', { name: 'Preencher onboarding' })).toHaveAttribute('href', '/onboarding')
  expect(screen.getByRole('navigation', { name: 'Navegação da área do cliente' })).toBeInTheDocument()
  expect(screen.getByRole('link', { name: 'Início' })).toHaveAttribute('aria-current', 'page')
})

test('does not reload client navigation data for ordinary activity', async () => {
  sessionStorage.setItem(
    'academia.session',
    JSON.stringify({ accessToken: 'access-token', refreshToken: 'refresh-token', expiresAt: Date.now() + 300_000, lastActivityAt: Date.now(), roles: ['client'] }),
  )
  const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: async () => ({ status: 'draft' }) })
  vi.stubGlobal('fetch', fetchMock)

  render(<App />)

  await screen.findByRole('link', { name: 'Onboarding' })
  fireEvent.pointerDown(document.body)
  await new Promise((resolve) => window.setTimeout(resolve, 0))

  expect(fetchMock).toHaveBeenCalledOnce()
  expect(screen.getByRole('link', { name: 'Onboarding' })).toBeInTheDocument()
})

test('navigates between client views without leaving the application', async () => {
  sessionStorage.setItem(
    'academia.session',
    JSON.stringify({ accessToken: 'access-token', refreshToken: 'refresh-token', expiresAt: Date.now() + 300_000, lastActivityAt: Date.now(), roles: ['client'] }),
  )
  vi.stubGlobal('fetch', vi.fn((url: string) => {
    if (url.endsWith('/onboarding/me')) return Promise.resolve({ ok: true, json: async () => ({ status: 'completed' }) })
    if (url.endsWith('/training/current')) return Promise.resolve({ ok: true, json: async () => ({ plan: null }) })
    return Promise.resolve({ ok: true, json: async () => [] })
  }))

  render(<App />)

  fireEvent.click(await screen.findByRole('link', { name: 'Ver meu treino' }))

  expect(await screen.findByRole('heading', { name: 'Meu treino' })).toBeInTheDocument()
  expect(window.location.pathname).toBe('/treino')
})

test('shows administrative dashboard and client management to an administrator', async () => {
  sessionStorage.setItem(
    'academia.session',
    JSON.stringify({ accessToken: 'access-token', refreshToken: 'refresh-token', expiresAt: Date.now() + 300_000, lastActivityAt: Date.now(), roles: ['admin'] }),
  )
  window.history.replaceState({}, '', '/admin')
  vi.stubGlobal('fetch', vi.fn((url: string) => {
    if (url.endsWith('/admin/dashboard/active-clients')) return Promise.resolve({ ok: true, json: async () => ({ active_clients: 0 }) })
    if (url.endsWith('/admin/dashboard/attendance')) return Promise.resolve({ ok: true, json: async () => ({ weeks: [] }) })
    if (url.endsWith('/admin/dashboard/occupancy')) return Promise.resolve({ ok: true, json: async () => ({ occupancy: 0, status: 'stale', updated_at: null }) })
    return Promise.resolve({ ok: true, json: async () => [] })
  }))

  render(<App />)

  expect(screen.getByRole('link', { name: 'Gerenciar equipamentos' })).toHaveAttribute('href', '/admin/equipamentos')
  expect(screen.getByRole('link', { name: 'Moderar publicações' })).toHaveAttribute('href', '/admin/publicacoes')
  expect(await screen.findByRole('heading', { name: 'Painel administrativo' })).toBeInTheDocument()
  expect(screen.getByRole('heading', { name: 'Indicadores da academia' })).toBeInTheDocument()
})

test('opens the administrative panel directly after an administrator signs in', async () => {
  sessionStorage.setItem(
    'academia.session',
    JSON.stringify({ accessToken: 'access-token', refreshToken: 'refresh-token', expiresAt: Date.now() + 300_000, lastActivityAt: Date.now(), roles: ['admin'] }),
  )
  vi.stubGlobal('fetch', vi.fn((url: string) => {
    if (url.endsWith('/admin/dashboard/active-clients')) return Promise.resolve({ ok: true, json: async () => ({ active_clients: 0 }) })
    if (url.endsWith('/admin/dashboard/attendance')) return Promise.resolve({ ok: true, json: async () => ({ weeks: [] }) })
    if (url.endsWith('/admin/dashboard/occupancy')) return Promise.resolve({ ok: true, json: async () => ({ occupancy: 0, status: 'stale', updated_at: null }) })
    return Promise.resolve({ ok: true, json: async () => [] })
  }))

  render(<App />)

  expect(await screen.findByRole('heading', { name: 'Painel administrativo' })).toBeInTheDocument()
  expect(screen.queryByRole('heading', { name: 'Bem-vindo à Academia Inteligente' })).not.toBeInTheDocument()
})

test('returns to the sign-in state when the client API rejects a stale session', async () => {
  const startLogin = vi.spyOn(OidcSessionClient.prototype, 'startLogin').mockResolvedValue()
  sessionStorage.setItem(
    'academia.session',
    JSON.stringify({ accessToken: 'stale-token', refreshToken: 'refresh-token', expiresAt: Date.now() + 300_000, lastActivityAt: Date.now(), roles: ['admin'] }),
  )
  window.history.replaceState({}, '', '/admin')
  vi.stubGlobal(
    'fetch',
    vi.fn().mockResolvedValue({ ok: false, status: 401, json: async () => ({ detail: 'Unauthenticated' }) }),
  )

  render(<App />)

  expect(await screen.findByText('Redirecionando para o login')).toBeInTheDocument()
  expect(startLogin).toHaveBeenCalledOnce()
  expect(sessionStorage.getItem('academia.session')).toBeNull()
})

test('ends the provider session and clears the local session when signing out', () => {
  sessionStorage.setItem(
    'academia.session',
    JSON.stringify({
      accessToken: 'access-token',
      refreshToken: 'refresh-token',
      idToken: 'id-token',
      expiresAt: Date.now() + 300_000,
      lastActivityAt: Date.now(),
      roles: ['admin'],
    }),
  )
  const logoutUrl = new OidcSessionClient().endSession()

  expect(sessionStorage.getItem('academia.session')).toBeNull()
  expect(logoutUrl.href).toBe(
    'http://localhost:8080/realms/academia/protocol/openid-connect/logout?client_id=academia-web&post_logout_redirect_uri=http%3A%2F%2Flocalhost%3A5173%2F&id_token_hint=id-token',
  )
})
