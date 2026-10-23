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
      { role: 'assistant', content: 'Faça com controle.', created_at: '2026-09-22T00:00:01Z', reference_citations: [{ passage_id: 'passage', title: 'Manual de exercícios', version: 2, location: 'page:3;passage:4' }] },
    ] }) })
  vi.stubGlobal('fetch', fetchMock)
  vi.stubGlobal('crypto', { randomUUID: () => '00000000-0000-4000-8000-000000000016' })

  render(<TrainingChatPage accessToken="access-token" onSignOut={vi.fn()} />)
  expect(await screen.findByText('Seu espaço para tirar dúvidas')).toBeInTheDocument()
  fireEvent.change(screen.getByLabelText('Escreva sua pergunta'), { target: { value: 'Como faço o agachamento?' } })
  fireEvent.keyDown(screen.getByLabelText('Escreva sua pergunta'), { key: 'Enter' })
  expect(await screen.findByText('Faça com controle.')).toBeInTheDocument()
  expect(screen.getByLabelText('Referências de apoio')).toHaveTextContent('Manual de exercícios · versão 2 · página 3 · trecho 4')
  expect(fetchMock.mock.calls[3][0]).toBe('http://localhost:8000/training/chat/messages')
  expect(JSON.parse(fetchMock.mock.calls[3][1].body)).toEqual({
    message: 'Como faço o agachamento?', client_request_id: '00000000-0000-4000-8000-000000000016',
  })
})

test.each([503, 500])('allows retry after HTTP %s with the same UUID and an editable composer', async (status) => {
  const fetchMock = vi.fn()
    .mockResolvedValueOnce({ ok: true, json: async () => ({ messages: [] }) })
    .mockResolvedValueOnce({ ok: true, json: async () => [] })
    .mockResolvedValueOnce({ ok: true, json: async () => ({ plan: null }) })
    .mockResolvedValueOnce({ ok: false, status })
    .mockResolvedValueOnce({ ok: true, json: async () => ({ messages: [] }) })
  vi.stubGlobal('fetch', fetchMock)
  vi.stubGlobal('crypto', { randomUUID: () => '00000000-0000-4000-8000-000000000017' })

  render(<TrainingChatPage accessToken="access-token" onSignOut={vi.fn()} />)
  await screen.findByText('Seu espaço para tirar dúvidas')
  expect(screen.getByText(/Seu plano atual só muda após revisão profissional/)).toBeInTheDocument()
  fireEvent.change(screen.getByLabelText('Escreva sua pergunta'), { target: { value: 'Troque meu exercício' } })
  fireEvent.click(screen.getByRole('button', { name: 'Enviar' }))
  expect(await screen.findByText(status === 503
    ? 'O assistente de treino está indisponível no momento. Tente novamente.'
    : 'Não foi possível enviar sua mensagem. Tente novamente.')).toBeInTheDocument()
  expect(screen.getByLabelText('Escreva sua pergunta')).toBeEnabled()
  expect(screen.getByLabelText('Escreva sua pergunta')).toHaveValue('Troque meu exercício')
  expect(screen.getByRole('button', { name: 'Enviar' })).toBeEnabled()
  fireEvent.click(screen.getByRole('button', { name: 'Tentar novamente' }))
  await screen.findByText('Seu espaço para tirar dúvidas')
  expect(JSON.parse(fetchMock.mock.calls[3][1].body).client_request_id).toBe(
    JSON.parse(fetchMock.mock.calls[4][1].body).client_request_id,
  )
  await waitFor(() => expect(screen.getByLabelText('Escreva sua pergunta')).toHaveValue(''))
  expect(screen.getByLabelText('Escreva sua pergunta')).toBeEnabled()
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

test('keeps multiline messages editable without sending Shift+Enter', async () => {
  const fetchMock = vi.fn()
    .mockResolvedValueOnce({ ok: true, json: async () => ({ messages: [] }) })
    .mockResolvedValueOnce({ ok: true, json: async () => [] })
    .mockResolvedValueOnce({ ok: true, json: async () => ({ plan: null }) })
  vi.stubGlobal('fetch', fetchMock)
  render(<TrainingChatPage accessToken="access-token" onSignOut={vi.fn()} />)
  await screen.findByText('Seu espaço para tirar dúvidas')
  const input = screen.getByLabelText('Escreva sua pergunta')
  fireEvent.change(input, { target: { value: 'Treino dois dias\nPrefiro manhã' } })
  fireEvent.keyDown(input, { key: 'Enter', shiftKey: true })
  expect(fetchMock).toHaveBeenCalledTimes(3)
  expect(input).toHaveValue('Treino dois dias\nPrefiro manhã')
  expect(screen.getByText(/corrigir apenas um dado/)).toBeInTheDocument()
})

test('shows initial conversation failures instead of a permanent spinner', async () => {
  vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('Falha de conexão')))
  render(<TrainingChatPage accessToken="access-token" onSignOut={vi.fn()} />)
  expect(await screen.findByText('Falha de conexão')).toBeInTheDocument()
  expect(screen.queryByText('Carregando assistente de treino')).not.toBeInTheDocument()
})

test('shows the sent message immediately while the request is still running', async () => {
  const fetchMock = vi.fn()
    .mockResolvedValueOnce({ ok: true, json: async () => ({ messages: [] }) })
    .mockResolvedValueOnce({ ok: true, json: async () => [] })
    .mockResolvedValueOnce({ ok: true, json: async () => ({ plan: null }) })
    .mockImplementationOnce(() => new Promise(() => {}))
  vi.stubGlobal('fetch', fetchMock)
  vi.stubGlobal('crypto', { randomUUID: () => 'request-1' })
  render(<TrainingChatPage accessToken="token" onSignOut={vi.fn()} />)
  await screen.findByText('Seu espaço para tirar dúvidas')
  fireEvent.change(screen.getByLabelText('Escreva sua pergunta'), { target: { value: 'Quero criar um novo treino' } })
  fireEvent.click(screen.getByRole('button', { name: 'Enviar' }))
  expect(await screen.findByText('Quero criar um novo treino')).toBeInTheDocument()
  expect(screen.getByRole('status', { name: 'Status da solicitação' })).toHaveTextContent('Enviando sua mensagem')
})

test('restores processing status on refresh and polls for the completed reply', async () => {
  const userMessage = { role: 'user', content: 'Quero criar um novo treino', client_request_id: 'request-1', created_at: '2026-10-22T22:00:00Z' }
  const fetchMock = vi.fn()
    .mockResolvedValueOnce({ ok: true, json: async () => ({ messages: [userMessage], pending_request: { client_request_id: 'request-1', status: 'processing', failure_code: null } }) })
    .mockResolvedValueOnce({ ok: true, json: async () => [] })
    .mockResolvedValueOnce({ ok: true, json: async () => ({ plan: null }) })
    .mockResolvedValueOnce({ ok: true, json: async () => ({ messages: [userMessage, { role: 'assistant', content: 'Criei seu rascunho.', reply_to_client_request_id: 'request-1', created_at: '2026-10-22T22:00:20Z' }], pending_request: null }) })
  vi.stubGlobal('fetch', fetchMock)
  render(<TrainingChatPage accessToken="token" onSignOut={vi.fn()} />)
  expect(await screen.findByText('Quero criar um novo treino')).toBeInTheDocument()
  expect(screen.getByRole('status', { name: 'Status da solicitação' })).toHaveTextContent('O assistente está processando sua solicitação')
  expect(screen.getByRole('button', { name: 'Processando…' })).toBeDisabled()
  expect(await screen.findByText('Criei seu rascunho.', {}, { timeout: 4000 })).toBeInTheDocument()
  expect(screen.queryByRole('status', { name: 'Status da solicitação' })).not.toBeInTheDocument()
  expect(fetchMock.mock.calls.every(([, init]) => init?.method !== 'POST')).toBe(true)
})

test('restores a timed-out request after reload and retries its saved UUID', async () => {
  const userMessage = { role: 'user', content: 'Quero criar um novo treino', client_request_id: 'saved-request', created_at: '2026-10-22T22:00:00Z' }
  const fetchMock = vi.fn()
    .mockResolvedValueOnce({ ok: true, json: async () => ({ messages: [userMessage], pending_request: { client_request_id: 'saved-request', status: 'failed', failure_code: 'deadline_exceeded' } }) })
    .mockResolvedValueOnce({ ok: true, json: async () => [] })
    .mockResolvedValueOnce({ ok: true, json: async () => ({ plan: null }) })
    .mockResolvedValueOnce({ ok: true, json: async () => ({ messages: [userMessage, { role: 'assistant', content: 'Criei seu rascunho.', reply_to_client_request_id: 'saved-request', created_at: '2026-10-22T22:01:00Z' }], pending_request: null }) })
  vi.stubGlobal('fetch', fetchMock)
  render(<TrainingChatPage accessToken="token" onSignOut={vi.fn()} />)
  expect(await screen.findByText(/não concluiu a resposta no tempo disponível/)).toBeInTheDocument()
  expect(screen.getByLabelText('Escreva sua pergunta')).toBeEnabled()
  fireEvent.click(screen.getByRole('button', { name: 'Tentar novamente' }))
  expect(await screen.findByText('Criei seu rascunho.')).toBeInTheDocument()
  expect(JSON.parse(fetchMock.mock.calls[3][1].body)).toEqual({ message: userMessage.content, client_request_id: 'saved-request' })
})

test('a failed status check reports uncertainty and recovers without resending', async () => {
  const state = { messages: [{ role: 'user', content: 'Olá', client_request_id: 'saved-request', created_at: '2026-10-22T22:00:00Z' }], pending_request: { client_request_id: 'saved-request', status: 'processing', failure_code: null } }
  const fetchMock = vi.fn()
    .mockResolvedValueOnce({ ok: true, json: async () => state })
    .mockResolvedValueOnce({ ok: true, json: async () => [] })
    .mockResolvedValueOnce({ ok: true, json: async () => ({ plan: null }) })
    .mockRejectedValueOnce(new Error('Disconnected'))
    .mockResolvedValueOnce({ ok: true, json: async () => ({ ...state, pending_request: { ...state.pending_request, status: 'failed', failure_code: 'deadline_exceeded' } }) })
  vi.stubGlobal('fetch', fetchMock)
  render(<TrainingChatPage accessToken="token" onSignOut={vi.fn()} />)
  expect(await screen.findByText(/Não foi possível verificar o andamento/, {}, { timeout: 3000 })).toBeInTheDocument()
  expect(await screen.findByText(/não concluiu a resposta no tempo disponível/, {}, { timeout: 3000 })).toBeInTheDocument()
  expect(screen.getByRole('button', { name: 'Tentar novamente' })).toBeEnabled()
  expect(fetchMock.mock.calls.every(([, init]) => init?.method !== 'POST')).toBe(true)
})
