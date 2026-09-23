import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, expect, test, vi } from 'vitest'

import { CurrentTrainingPage } from './current-training-page'

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

const currentPlan = {
  plan_id: 'plan-1',
  version_number: 1,
  status: 'current' as const,
  name: 'Força inicial',
  objective: 'Ganhar força com consistência',
  items: [
    {
      exercise_name: 'Agachamento',
      sets: 3,
      repetitions: '8',
      load_guidance: 'Carga confortável e técnica controlada',
      rest_seconds: 90,
      position: 1,
    },
  ],
}

test('renders the current training plan in workout order', async () => {
  const fetchMock = vi.fn()
    .mockResolvedValueOnce({ ok: true, json: async () => ({ plan: currentPlan }) })
    .mockResolvedValueOnce({ ok: true, json: async () => [] })
  vi.stubGlobal('fetch', fetchMock)

  render(<CurrentTrainingPage accessToken="access-token" onSignOut={vi.fn()} />)

  expect(await screen.findByRole('heading', { name: 'Meu treino' })).toBeInTheDocument()
  expect(screen.getByText('Força inicial')).toBeInTheDocument()
  expect(screen.getByText('Agachamento')).toBeInTheDocument()
  expect(screen.getByText('3 séries')).toBeInTheDocument()
  expect(screen.getByText('8 repetições')).toBeInTheDocument()
  expect(screen.getByText('Descanso: 90 s')).toBeInTheDocument()
  expect(fetchMock.mock.calls[0][0]).toBe('http://localhost:8000/training/current')
  expect(fetchMock.mock.calls[0][1]).toMatchObject({ headers: { Authorization: 'Bearer access-token' } })
})

test('shows an own draft as pending instructor approval, not as the current plan', async () => {
  const draft = { ...currentPlan, status: 'proposal', origin: 'ai', name: 'Rascunho de força' }
  vi.stubGlobal('fetch', vi.fn()
    .mockResolvedValueOnce({ ok: true, json: async () => ({ plan: null }) })
    .mockResolvedValueOnce({ ok: true, json: async () => [draft] }))

  render(<CurrentTrainingPage accessToken="access-token" onSignOut={vi.fn()} />)

  expect(await screen.findByText('Rascunho de força')).toBeInTheDocument()
  expect(screen.getByText('Rascunho — ainda não aprovado')).toBeInTheDocument()
  expect(screen.getByText(/Seu instrutor precisa revisar, aprovar e ativar/)).toBeInTheDocument()
})

test('renders a clear empty state when the client has no current plan', async () => {
  vi.stubGlobal('fetch', vi.fn()
    .mockResolvedValueOnce({ ok: true, json: async () => ({ plan: null }) })
    .mockResolvedValueOnce({ ok: true, json: async () => [] }))

  render(<CurrentTrainingPage accessToken="access-token" onSignOut={vi.fn()} />)

  expect(await screen.findByText('Seu treino ainda não está disponível')).toBeInTheDocument()
  expect(screen.getByRole('button', { name: 'Gerar rascunho inicial com IA' })).toBeInTheDocument()
})

test('generates and displays a single initial AI draft for the client', async () => {
  const draft = { ...currentPlan, status: 'proposal' as const, origin: 'ai' as const, name: 'Rascunho inicial de força' }
  const fetchMock = vi.fn()
    .mockResolvedValueOnce({ ok: true, json: async () => ({ plan: null }) })
    .mockResolvedValueOnce({ ok: true, json: async () => [] })
    .mockResolvedValueOnce({ ok: true, json: async () => draft })
  vi.stubGlobal('fetch', fetchMock)

  render(<CurrentTrainingPage accessToken="access-token" onSignOut={vi.fn()} />)
  fireEvent.click(await screen.findByRole('button', { name: 'Gerar rascunho inicial com IA' }))

  expect(await screen.findByText('Rascunho inicial de força')).toBeInTheDocument()
  expect(fetchMock.mock.calls[2][0]).toBe('http://localhost:8000/training/initial-proposal')
  expect(fetchMock.mock.calls[2][1]).toMatchObject({ method: 'POST', headers: { Authorization: 'Bearer access-token' } })
  expect(screen.queryByRole('button', { name: 'Gerar rascunho inicial com IA' })).not.toBeInTheDocument()
})

test('renders a controlled error when the current-plan query fails', async () => {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: false, status: 500 }))

  render(<CurrentTrainingPage accessToken="access-token" onSignOut={vi.fn()} />)

  expect(await screen.findByText('Não foi possível carregar seu treino. Tente novamente.')).toBeInTheDocument()
  expect(screen.getByRole('button', { name: 'Tentar novamente' })).toBeInTheDocument()
})
