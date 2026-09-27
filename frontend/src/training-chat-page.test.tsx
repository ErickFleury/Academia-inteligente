import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, expect, test, vi } from 'vitest'

import { TrainingChatPage } from './training-chat-page'

vi.mock('./occupancy', () => ({ getOccupancy: async () => ({ occupancy: 0 }) }))

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

test('sends a Portuguese client training-chat message with a frontend UUID', async () => {
  const fetchMock = vi.fn()
    .mockResolvedValueOnce({ ok: true, json: async () => ({ messages: [] }) })
    .mockResolvedValueOnce({ ok: true, json: async () => [] })
    .mockResolvedValueOnce({ ok: true, json: async () => ({ plan: null }) })
    .mockResolvedValueOnce({ ok: true, json: async () => ({ messages: [
      { role: 'user', content: 'Como faço o agachamento?', created_at: '2026-09-22T00:00:00Z' },
      { role: 'assistant', content: 'Faça com controle.', created_at: '2026-09-22T00:00:01Z' },
    ] }) })
  vi.stubGlobal('fetch', fetchMock)
  vi.stubGlobal('crypto', { randomUUID: () => '00000000-0000-4000-8000-000000000016' })

  render(<TrainingChatPage accessToken="access-token" onSignOut={vi.fn()} />)
  expect(await screen.findByText('Seu espaço para tirar dúvidas')).toBeInTheDocument()
  fireEvent.change(screen.getByLabelText('Escreva sua pergunta'), { target: { value: 'Como faço o agachamento?' } })
  fireEvent.keyDown(screen.getByLabelText('Escreva sua pergunta'), { key: 'Enter' })
  expect(await screen.findByText('Faça com controle.')).toBeInTheDocument()
  expect(fetchMock.mock.calls[3][0]).toBe('http://localhost:8000/training/chat/messages')
  expect(JSON.parse(fetchMock.mock.calls[3][1].body)).toEqual({
    message: 'Como faço o agachamento?', client_request_id: '00000000-0000-4000-8000-000000000016',
  })
})

test('reuses its client request UUID for a retry and explains the draft-review boundary', async () => {
  const fetchMock = vi.fn()
    .mockResolvedValueOnce({ ok: true, json: async () => ({ messages: [] }) })
    .mockResolvedValueOnce({ ok: true, json: async () => [] })
    .mockResolvedValueOnce({ ok: true, json: async () => ({ plan: null }) })
    .mockResolvedValueOnce({ ok: false, status: 503 })
    .mockResolvedValueOnce({ ok: true, json: async () => ({ messages: [] }) })
  vi.stubGlobal('fetch', fetchMock)
  vi.stubGlobal('crypto', { randomUUID: () => '00000000-0000-4000-8000-000000000017' })

  render(<TrainingChatPage accessToken="access-token" onSignOut={vi.fn()} />)
  await screen.findByText('Seu espaço para tirar dúvidas')
  expect(screen.getByText(/Seu plano atual só muda após revisão profissional/)).toBeInTheDocument()
  fireEvent.change(screen.getByLabelText('Escreva sua pergunta'), { target: { value: 'Troque meu exercício' } })
  fireEvent.click(screen.getByRole('button', { name: 'Enviar' }))
  expect(await screen.findByText('O assistente de treino está indisponível no momento. Tente novamente.')).toBeInTheDocument()
  fireEvent.click(screen.getByRole('button', { name: 'Tentar novamente' }))
  await screen.findByText('Seu espaço para tirar dúvidas')
  expect(JSON.parse(fetchMock.mock.calls[3][1].body).client_request_id).toBe(
    JSON.parse(fetchMock.mock.calls[4][1].body).client_request_id,
  )
})

test('offers an AI-detected change for client confirmation before creating a proposal', async () => {
  const fetchMock = vi.fn()
    .mockResolvedValueOnce({ ok: true, json: async () => ({ messages: [
      {
        role: 'user', content: 'Meu joelho incomoda no agachamento.',
        created_at: '2026-09-23T00:00:00Z', client_request_id: '00000000-0000-4000-8000-000000000018',
      },
      {
        role: 'assistant', content: 'Posso preparar uma proposta para revisão.',
        created_at: '2026-09-23T00:00:01Z', reply_to_client_request_id: '00000000-0000-4000-8000-000000000018',
        adaptation_suggested: true, adaptation_reason: 'Desconforto relatado no agachamento.',
      },
    ] }) })
    .mockResolvedValueOnce({ ok: true, json: async () => [] })
    .mockResolvedValueOnce({ ok: true, json: async () => ({ plan: { plan_id: 'plan-1' } }) })
    .mockResolvedValueOnce({ ok: true, json: async () => ({
      id: 'proposal-1', status: 'proposed', source_client_request_id: '00000000-0000-4000-8000-000000000018', reason: 'Desconforto relatado no agachamento.',
      explanation: 'Uma proposta será enviada para sua revisão.', operations: [],
    }) })
  vi.stubGlobal('fetch', fetchMock)
  vi.stubGlobal('crypto', { randomUUID: () => '00000000-0000-4000-8000-000000000019' })

  render(<TrainingChatPage accessToken="access-token" onSignOut={vi.fn()} />)
  await screen.findByText('Sugestão de alteração')
  fireEvent.click(screen.getByRole('button', { name: 'Enviar rascunho para minha revisão' }))
  await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(4))
  expect(JSON.parse(fetchMock.mock.calls[3][1].body)).toMatchObject({
    source_client_request_id: '00000000-0000-4000-8000-000000000018',
  })
})
