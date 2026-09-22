import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, expect, test, vi } from 'vitest'

import { TrainingChatPage } from './training-chat-page'

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

test('sends a Portuguese client training-chat message with a frontend UUID', async () => {
  const fetchMock = vi.fn()
    .mockResolvedValueOnce({ ok: true, json: async () => ({ messages: [] }) })
    .mockResolvedValueOnce({ ok: true, json: async () => ({ messages: [
      { role: 'user', content: 'Como faço o agachamento?', created_at: '2026-09-22T00:00:00Z' },
      { role: 'assistant', content: 'Faça com controle.', created_at: '2026-09-22T00:00:01Z' },
    ] }) })
  vi.stubGlobal('fetch', fetchMock)
  vi.stubGlobal('crypto', { randomUUID: () => '00000000-0000-4000-8000-000000000016' })

  render(<TrainingChatPage accessToken="access-token" onSignOut={vi.fn()} />)
  expect(await screen.findByText('Seu espaço para tirar dúvidas')).toBeInTheDocument()
  fireEvent.change(screen.getByLabelText('Escreva sua pergunta'), { target: { value: 'Como faço o agachamento?' } })
  fireEvent.click(screen.getByRole('button', { name: 'Enviar' }))
  expect(await screen.findByText('Faça com controle.')).toBeInTheDocument()
  expect(fetchMock.mock.calls[1][0]).toBe('http://localhost:8000/training/chat/messages')
  expect(JSON.parse(fetchMock.mock.calls[1][1].body)).toEqual({
    message: 'Como faço o agachamento?', client_request_id: '00000000-0000-4000-8000-000000000016',
  })
})

test('reuses its client request UUID for a retry and explains that chat cannot alter the plan', async () => {
  const fetchMock = vi.fn()
    .mockResolvedValueOnce({ ok: true, json: async () => ({ messages: [] }) })
    .mockResolvedValueOnce({ ok: false, status: 503 })
    .mockResolvedValueOnce({ ok: true, json: async () => ({ messages: [] }) })
  vi.stubGlobal('fetch', fetchMock)
  vi.stubGlobal('crypto', { randomUUID: () => '00000000-0000-4000-8000-000000000017' })

  render(<TrainingChatPage accessToken="access-token" onSignOut={vi.fn()} />)
  await screen.findByText('Seu espaço para tirar dúvidas')
  expect(screen.getByText('O assistente explica seu treino, mas não altera o seu plano.')).toBeInTheDocument()
  fireEvent.change(screen.getByLabelText('Escreva sua pergunta'), { target: { value: 'Troque meu exercício' } })
  fireEvent.click(screen.getByRole('button', { name: 'Enviar' }))
  expect(await screen.findByText('O assistente de treino está indisponível no momento. Tente novamente.')).toBeInTheDocument()
  fireEvent.click(screen.getByRole('button', { name: 'Tentar novamente' }))
  await screen.findByText('Seu espaço para tirar dúvidas')
  expect(JSON.parse(fetchMock.mock.calls[1][1].body).client_request_id).toBe(
    JSON.parse(fetchMock.mock.calls[2][1].body).client_request_id,
  )
})
