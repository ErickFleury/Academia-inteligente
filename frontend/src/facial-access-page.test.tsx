import { act, cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { ThemeProvider } from '@mui/material'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, expect, test, vi } from 'vitest'

import { FacialAccessPage } from './facial-access-page'
import type { AccessAttempt } from './facial-access'
import { theme } from './theme'

vi.mock('./components/webcam-capture', () => ({ WebcamCapture: ({ open, onCapture, onClose }: { open: boolean; onCapture: (image: Blob) => Promise<void>; onClose: () => void }) => open ? <button onClick={() => { void onCapture(new Blob(['synthetic'])).then(onClose) }}>Captura de teste</button> : null }))
afterEach(() => { cleanup(); vi.useRealTimers(); vi.restoreAllMocks(); vi.unstubAllGlobals() })

function setup(options: { uncertain?: boolean; denied?: boolean; offline?: boolean; correctionConflict?: boolean } = {}) {
  let count = 0
  let captures = 0
  let confirmationLost = false
  let state = { client_id: 'client', client_name: 'Ana Silva', inside: false, revision: 0, client_active: true }
  let attempt: AccessAttempt = { attempt_id: 'attempt', direction: 'entry', status: 'awaiting_capture', result_code: 'capture_required', captures: 0, expires_at: new Date(Date.now() + 900_000).toISOString(), client_id: null, client_name: null, release_request_id: null, release_mode: null, can_retry: false }
  const response = (data: unknown) => ({ ok: true, json: async () => data })
  const fetchMock = vi.fn(async (url: string, init?: RequestInit) => {
    if (url.endsWith('/clients')) return response([{ id: 'client', name: 'Ana Silva', client_active: true }])
    if (url.endsWith('/provider-status')) return response({ mode: 'pilot', available: !options.offline, cleanup_pending: 0 })
    if (url.endsWith('/pilot-heartbeat')) return response({ status: 'current' })
    if (url.endsWith('/occupancy')) return response({ occupancy: count, status: 'current', updated_at: null })
    if (url.includes('/events?')) return response({ items: [{ id: 'event', kind: 'audit', operation: 'access_capture', result: 'authorized', direction: 'entry', person_name: 'Ana Silva', client_id: 'client', occurred_at: '2026-09-27T12:00:00Z', reason: null }], next_cursor: null })
    if (url.endsWith('/state')) return response(state)
    if (url.endsWith('/state-corrections')) {
      if (options.correctionConflict) { state = { ...state, inside: true, revision: 1 }; return { ok: false, status: 409, json: async () => ({ detail: 'state_changed' }) } }
      const data = JSON.parse(init!.body as string) as { inside: boolean }
      state = { ...state, inside: data.inside, revision: state.revision + 1 }; count = Number(state.inside)
      return response({ status: 'corrected', correction_id: 'correction', state, occupancy: count })
    }
    if (url.endsWith('/access-attempts')) { const body = JSON.parse(init!.body as string) as { direction: 'entry' | 'exit' }; attempt = { ...attempt, direction: body.direction }; return response(attempt) }
    if (url.endsWith('/capture')) {
      captures += 1
      attempt = options.denied ? { ...attempt, status: captures < 2 ? 'rejected' : 'failed', result_code: 'unknown_face', captures, can_retry: captures < 2 } : { ...attempt, status: 'authorized', result_code: 'authorized', captures, client_id: 'client', client_name: 'Ana Silva', release_mode: 'simulated', release_request_id: 'release', expires_at: new Date(Date.now() + 30_000).toISOString() }
      if (options.uncertain) throw new TypeError('network unavailable')
      return response(attempt)
    }
    if (url.endsWith('/passage')) {
      count = 1; attempt = { ...attempt, status: 'confirmed', result_code: 'passage_confirmed' }
      if (options.uncertain && !confirmationLost) { confirmationLost = true; throw new TypeError('network unavailable') }
      return response({ status: 'confirmed', attempt_id: 'attempt', state: { ...state, inside: true }, occupancy: count })
    }
    if (url.endsWith('/cancel')) { attempt = { ...attempt, status: 'canceled', result_code: 'attempt_canceled' }; return response(attempt) }
    if (url.endsWith('/access-attempts/attempt')) return response(attempt)
    throw new Error(`Unexpected test URL: ${url}`)
  })
  vi.stubGlobal('fetch', fetchMock)
  const view = render(<ThemeProvider theme={theme}><MemoryRouter><FacialAccessPage accessToken="token" onSignOut={vi.fn()} onUnauthenticated={vi.fn()} /></MemoryRouter></ThemeProvider>)
  return { ...view, fetchMock }
}

async function scan() {
  await screen.findByText('Reconhecimento disponível')
  fireEvent.click(screen.getByRole('button', { name: 'Reconhecer rosto' }))
  fireEvent.click(await screen.findByRole('button', { name: 'Captura de teste' }))
}

test('recognition records a simulated release and requires separate passage confirmation', async () => {
  const { fetchMock } = setup()
  await scan()
  expect(await screen.findByText('Simulação: liberação solicitada')).toBeInTheDocument()
  expect(screen.getByText('0 pessoas na academia')).toBeInTheDocument()
  const panel = screen.getByRole('region', { name: 'Teste de passagem' })
  expect(within(panel).getByText('Cliente: Ana Silva')).toBeInTheDocument()
  expect(fetchMock.mock.calls.filter(([url]) => url.endsWith('/passage'))).toHaveLength(0)
  fireEvent.click(screen.getByRole('button', { name: 'Confirmar passagem' }))
  expect(await screen.findByText('1 pessoa na academia')).toBeInTheDocument()
  expect(fetchMock.mock.calls.filter(([url]) => url.endsWith('/passage'))).toHaveLength(1)
  const capture = fetchMock.mock.calls.find(([url]) => url.endsWith('/capture'))!
  expect(capture[1]?.body).toBeInstanceOf(FormData)
  expect(capture[1]?.headers).not.toHaveProperty('Content-Type')
})

test('uncertain capture and passage recover by polling without replaying the image or passage', async () => {
  const { fetchMock } = setup({ uncertain: true })
  await scan()
  expect(await screen.findByText(/Consulte o resultado antes/)).toBeInTheDocument()
  expect(screen.queryByRole('button', { name: 'Confirmar passagem' })).not.toBeInTheDocument()
  fireEvent.click(screen.getByRole('button', { name: 'Consultar resultado' }))
  fireEvent.click(await screen.findByRole('button', { name: 'Confirmar passagem' }))
  await waitFor(() => expect(screen.getByRole('button', { name: 'Consultar resultado' })).toBeEnabled())
  fireEvent.click(screen.getByRole('button', { name: 'Consultar resultado' }))
  expect(await screen.findByText('Passagem confirmada')).toBeInTheDocument()
  expect(fetchMock.mock.calls.filter(([url]) => url.endsWith('/capture'))).toHaveLength(1)
  expect(fetchMock.mock.calls.filter(([url]) => url.endsWith('/passage'))).toHaveLength(1)
})

test('failed matching offers only one further capture and changing direction cancels the old attempt', async () => {
  const { fetchMock } = setup({ denied: true })
  await scan()
  fireEvent.click(await screen.findByRole('button', { name: 'Tentar outra captura' }))
  fireEvent.click(await screen.findByRole('button', { name: 'Captura de teste' }))
  await waitFor(() => expect(screen.queryByRole('button', { name: 'Tentar outra captura' })).not.toBeInTheDocument())
  expect(screen.queryByRole('button', { name: 'Confirmar passagem' })).not.toBeInTheDocument()
  fireEvent.click(screen.getByRole('button', { name: 'Saída' }))
  await waitFor(() => expect(fetchMock.mock.calls.some(([url]) => url.endsWith('/cancel'))).toBe(true))
  expect(fetchMock.mock.calls.filter(([url]) => url.endsWith('/capture'))).toHaveLength(2)
})

test('correction requires a reason and sends the displayed client revision', async () => {
  const { fetchMock } = setup()
  await screen.findByText('Reconhecimento disponível')
  fireEvent.mouseDown(screen.getByRole('combobox', { name: 'Cliente para correção' }))
  fireEvent.click(await screen.findByRole('option', { name: 'Ana Silva' }))
  expect(await screen.findByText('Fora da academia')).toBeInTheDocument()
  expect(screen.getByRole('button', { name: 'Aplicar correção' })).toBeDisabled()
  fireEvent.mouseDown(screen.getByRole('combobox', { name: 'Estado correto' }))
  fireEvent.click(screen.getByRole('option', { name: 'Dentro da academia' }))
  fireEvent.change(screen.getByRole('textbox', { name: /Motivo da correção/ }), { target: { value: 'Entrada não registrada' } })
  fireEvent.click(screen.getByRole('button', { name: 'Aplicar correção' }))
  expect(await screen.findByText('Presença corrigida e contagem atualizada.')).toBeInTheDocument()
  const call = fetchMock.mock.calls.find(([url]) => url.endsWith('/state-corrections'))!
  expect(JSON.parse(call[1]!.body as string)).toMatchObject({ client_id: 'client', inside: true, expected_revision: 0, reason: 'Entrada não registrada' })
})

test('history filters use safe query parameters and unavailable service disables recognition', async () => {
  const { fetchMock } = setup({ offline: true })
  await screen.findByText('Reconhecimento indisponível')
  expect(screen.getByRole('button', { name: 'Reconhecer rosto' })).toBeDisabled()
  expect(fetchMock.mock.calls.some(([url]) => url.endsWith('/pilot-heartbeat'))).toBe(false)
  fireEvent.mouseDown(screen.getByRole('combobox', { name: 'Filtrar por sentido' }))
  fireEvent.click(screen.getByRole('option', { name: 'Saída' }))
  await waitFor(() => expect(fetchMock.mock.calls.some(([url]) => url.includes('direction=exit'))).toBe(true))
  expect(screen.queryByText('Captura de teste')).not.toBeInTheDocument()
})

test('heartbeat runs every minute only while the panel is mounted', async () => {
  vi.useFakeTimers()
  let view!: ReturnType<typeof setup>
  await act(async () => { view = setup() })
  const beats = () => view.fetchMock.mock.calls.filter(([url]) => url.endsWith('/pilot-heartbeat')).length
  expect(beats()).toBe(1)
  await act(async () => { await vi.advanceTimersByTimeAsync(60_000) })
  expect(beats()).toBe(2)
  view.unmount()
  await act(async () => { await vi.advanceTimersByTimeAsync(60_000) })
  expect(beats()).toBe(2)
})

test('an expired authorization no longer offers passage confirmation', async () => {
  vi.useFakeTimers()
  await act(async () => { setup() })
  await act(async () => { fireEvent.click(screen.getByRole('button', { name: 'Reconhecer rosto' })) })
  await act(async () => { fireEvent.click(screen.getByRole('button', { name: 'Captura de teste' })) })
  expect(screen.getByRole('button', { name: 'Confirmar passagem' })).toBeEnabled()
  await act(async () => { await vi.advanceTimersByTimeAsync(31_000) })
  expect(screen.queryByRole('button', { name: 'Confirmar passagem' })).not.toBeInTheDocument()
  expect(screen.getByText('A autorização expirou. Inicie uma nova tentativa.')).toBeInTheDocument()
})

test('a competing correction refreshes the displayed state and preserves the reason', async () => {
  setup({ correctionConflict: true })
  await screen.findByText('Reconhecimento disponível')
  fireEvent.mouseDown(screen.getByRole('combobox', { name: 'Cliente para correção' }))
  fireEvent.click(await screen.findByRole('option', { name: 'Ana Silva' }))
  await screen.findByText('Fora da academia')
  fireEvent.change(screen.getByRole('textbox', { name: /Motivo da correção/ }), { target: { value: 'Conferência de saída' } })
  fireEvent.click(screen.getByRole('button', { name: 'Aplicar correção' }))
  expect(await screen.findByText(/A presença mudou em outra operação/)).toBeInTheDocument()
  expect(await screen.findByText('Dentro da academia')).toBeInTheDocument()
  expect(screen.getByRole('textbox', { name: /Motivo da correção/ })).toHaveValue('Conferência de saída')
})
