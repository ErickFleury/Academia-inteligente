import { cleanup, render, screen } from '@testing-library/react'
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
  const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: async () => ({ plan: currentPlan }) })
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

test('renders a clear empty state when the client has no current plan', async () => {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, json: async () => ({ plan: null }) }))

  render(<CurrentTrainingPage accessToken="access-token" onSignOut={vi.fn()} />)

  expect(await screen.findByText('Seu treino ainda não está disponível')).toBeInTheDocument()
})

test('renders a controlled error when the current-plan query fails', async () => {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: false, status: 500 }))

  render(<CurrentTrainingPage accessToken="access-token" onSignOut={vi.fn()} />)

  expect(await screen.findByText('Não foi possível carregar seu treino. Tente novamente.')).toBeInTheDocument()
  expect(screen.getByRole('button', { name: 'Tentar novamente' })).toBeInTheDocument()
})
