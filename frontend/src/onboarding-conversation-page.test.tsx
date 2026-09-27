import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, expect, test, vi } from 'vitest'

import { OnboardingConversationPage } from './onboarding-conversation-page'

vi.mock('./occupancy', () => ({ getOccupancy: async () => ({ occupancy: 0 }) }))

const emptyConversation = {
  messages: [],
  missing_required_fields: ['training_goal', 'height_cm'],
  completion_ready: false,
}

const emptyDraft = {
  status: 'draft', completed_at: null, training_goal: null, training_experience: null,
  height_cm: null, weight_kg: null, has_limitations_or_complaints: null,
  limitations_or_complaints: null, uses_medications: null, medications: null,
  has_health_conditions: null, health_conditions: null,
}

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

test('starts a mobile-friendly conversation and shows structured progress', async () => {
  const fetchMock = vi
    .fn()
    .mockResolvedValueOnce({ ok: true, json: async () => emptyConversation })
    .mockResolvedValueOnce({ ok: true, json: async () => emptyDraft })
    .mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        messages: [
          { role: 'user', content: 'Quero começar meu onboarding.', created_at: '2026-09-21T00:00:00Z' },
          { role: 'assistant', content: 'Qual é o seu objetivo?', created_at: '2026-09-21T00:00:01Z' },
        ],
        missing_required_fields: ['training_goal'],
        completion_ready: false,
      }),
    })
  vi.stubGlobal('fetch', fetchMock)
  vi.stubGlobal('crypto', { randomUUID: () => '00000000-0000-4000-8000-000000000001' })

  render(<OnboardingConversationPage accessToken="access-token" onSignOut={vi.fn()} />)

  expect(await screen.findByText('Comece quando estiver pronto')).toBeInTheDocument()
  expect(screen.getByText('objetivo de treino')).toBeInTheDocument()
  fireEvent.click(screen.getByRole('button', { name: 'Começar conversa' }))

  expect(await screen.findByText('Qual é o seu objetivo?')).toBeInTheDocument()
  expect(fetchMock.mock.calls[2][0]).toBe('http://localhost:8000/onboarding/conversation/messages')
  expect(JSON.parse(fetchMock.mock.calls[2][1].body)).toEqual({
    message: 'Quero começar meu onboarding.',
    client_request_id: '00000000-0000-4000-8000-000000000001',
  })
})

test('reuses the same client request id when a conversation submission is retried', async () => {
  const fetchMock = vi
    .fn()
    .mockResolvedValueOnce({ ok: true, json: async () => emptyConversation })
    .mockResolvedValueOnce({ ok: true, json: async () => emptyDraft })
    .mockResolvedValueOnce({ ok: false, status: 503, json: async () => ({}) })
    .mockResolvedValueOnce({ ok: true, json: async () => emptyConversation })
  vi.stubGlobal('fetch', fetchMock)
  vi.stubGlobal('crypto', { randomUUID: () => '00000000-0000-4000-8000-000000000002' })

  render(<OnboardingConversationPage accessToken="access-token" onSignOut={vi.fn()} />)

  await screen.findByText('Comece quando estiver pronto')
  fireEvent.change(screen.getByLabelText('Escreva sua resposta'), { target: { value: 'Meu objetivo é força' } })
  fireEvent.keyDown(screen.getByLabelText('Escreva sua resposta'), { key: 'Enter' })
  expect(await screen.findByText('A conversa está indisponível no momento. Tente novamente.')).toBeInTheDocument()
  fireEvent.click(screen.getByRole('button', { name: 'Tentar novamente' }))

  await screen.findByText('Comece quando estiver pronto')
  expect(JSON.parse(fetchMock.mock.calls[2][1].body).client_request_id).toBe(
    JSON.parse(fetchMock.mock.calls[3][1].body).client_request_id,
  )
})

test('keeps corrections available until explicit onboarding completion', async () => {
  const fetchMock = vi
    .fn()
    .mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        messages: [{ role: 'assistant', content: 'Já reuni todas as informações necessárias.', created_at: '2026-09-22T00:00:00Z' }],
        missing_required_fields: [],
        completion_ready: true,
      }),
    })
    .mockResolvedValueOnce({ ok: true, json: async () => ({ ...emptyDraft, status: 'draft' }) })
  vi.stubGlobal('fetch', fetchMock)

  render(<OnboardingConversationPage accessToken="access-token" onSignOut={vi.fn()} />)

  expect(await screen.findByText('Já reuni todas as informações necessárias.')).toBeInTheDocument()
  expect(screen.getByLabelText('Escreva sua resposta')).toBeInTheDocument()
  expect(screen.getByRole('link', { name: 'Revisar e confirmar informações' })).toHaveAttribute('href', '/onboarding')
  expect(screen.queryByText('Revisar e concluir')).not.toBeInTheDocument()
})

test('shows collected facts and clarification without submitting Shift+Enter', async () => {
  const fetchMock = vi.fn()
    .mockResolvedValueOnce({ ok: true, json: async () => ({ ...emptyConversation, known_answers: { height_cm: 180, weight_kg: 82 }, clarification_fields: ['weight_kg'], needs_clarification: true }) })
    .mockResolvedValueOnce({ ok: true, json: async () => emptyDraft })
  vi.stubGlobal('fetch', fetchMock)
  render(<OnboardingConversationPage accessToken="access-token" onSignOut={vi.fn()} />)
  expect(await screen.findByText('180 cm')).toBeInTheDocument()
  expect(screen.getByText('82 kg')).toBeInTheDocument()
  expect(screen.getByText('Precisamos confirmar: peso. As outras respostas foram mantidas.')).toBeInTheDocument()
  const input = screen.getByLabelText('Escreva sua resposta')
  fireEvent.change(input, { target: { value: 'Na verdade, 83 kg' } })
  fireEvent.keyDown(input, { key: 'Enter', shiftKey: true })
  expect(fetchMock).toHaveBeenCalledTimes(2)
})

test('shows an initial loading failure instead of remaining on the spinner', async () => {
  vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('Falha de conexão')))
  render(<OnboardingConversationPage accessToken="access-token" onSignOut={vi.fn()} />)
  expect(await screen.findByText('Falha de conexão')).toBeInTheDocument()
  expect(screen.queryByText('Carregando conversa de onboarding')).not.toBeInTheDocument()
})
