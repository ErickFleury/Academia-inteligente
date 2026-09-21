import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, expect, test, vi } from 'vitest'

import { OnboardingAccessPage } from './onboarding-access-page'

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

test('opens a valid token-bound onboarding entry without consuming it passively', async () => {
  const fetchMock = vi
    .fn()
    .mockResolvedValueOnce({ ok: true, json: async () => ({ status: 'valid' }) })
    .mockResolvedValueOnce({ ok: true, json: async () => ({ status: 'redeemed' }) })
  vi.stubGlobal('fetch', fetchMock)

  render(<OnboardingAccessPage token="invitation-token" />)

  expect(await screen.findByRole('heading', { name: 'Seu onboarding começa aqui' })).toBeInTheDocument()
  expect(fetchMock.mock.calls[0][0]).toBe('http://localhost:8000/onboarding/access?token=invitation-token')
  expect(fetchMock.mock.calls[0][1]).toMatchObject({ method: 'GET' })
  expect(screen.queryByText('invitation-token')).not.toBeInTheDocument()

  fireEvent.click(screen.getByRole('button', { name: 'Iniciar onboarding' }))
  expect(await screen.findByText(/Seu convite foi usado com segurança/i)).toBeInTheDocument()
  expect(fetchMock.mock.calls[1][0]).toBe('http://localhost:8000/onboarding/access/redemptions?token=invitation-token')
  expect(fetchMock.mock.calls[1][1]).toMatchObject({ method: 'POST' })
})

test.each([
  ['expired', 'Este convite expirou'],
  ['invalid', 'Este convite não está disponível'],
] as const)('shows a controlled %s invitation state', async (status, title) => {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, json: async () => ({ status }) }))

  render(<OnboardingAccessPage token="unavailable-token" />)

  expect(await screen.findByRole('heading', { name: title })).toBeInTheDocument()
  expect(screen.getByText('Não foi possível abrir o onboarding.')).toBeInTheDocument()
})

test('treats a missing or failed token validation as a controlled state', async () => {
  vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('network unavailable')))

  render(<OnboardingAccessPage token={null} />)

  expect(screen.getByRole('heading', { name: 'Este convite não está disponível' })).toBeInTheDocument()
  expect(screen.getByText('Não foi possível abrir o onboarding.')).toBeInTheDocument()
})
