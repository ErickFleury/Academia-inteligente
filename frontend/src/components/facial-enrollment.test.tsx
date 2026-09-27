import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, expect, test, vi } from 'vitest'

import { personBinding } from '../biometrics'
import { FacialEnrollment } from './facial-enrollment'

vi.mock('./webcam-capture', () => ({ WebcamCapture: ({ open, onCapture }: { open: boolean; onCapture: (image: Blob) => Promise<void> }) => open ? <button onClick={() => { void onCapture(new Blob(['synthetic'])).catch(() => undefined) }}>Captura de teste</button> : null }))
afterEach(() => { cleanup(); vi.unstubAllGlobals() })
const identity = { email: 'ada@example.test', cpf: '52998224725' }
const enabled = { person_id: 'person', status: 'enabled', revision: 1, cleanup_pending: false }

test('reuses a shared enrollment without opening camera and clears proof on identity change', async () => {
  const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: async () => enabled })
  vi.stubGlobal('fetch', fetchMock)
  const ready = vi.fn()
  const { rerender } = render(<FacialEnrollment token="token" {...identity} role="employee" onReady={ready} onUnauthenticated={vi.fn()} />)
  fireEvent.click(screen.getByRole('button', { name: 'Verificar cadastro facial' }))
  expect(await screen.findByText(/será reutilizado/)).toBeInTheDocument()
  expect(ready).toHaveBeenLastCalledWith({ binding: personBinding(identity.email, identity.cpf), sessionId: null, expiresAt: null })
  expect(screen.queryByText('Captura de teste')).not.toBeInTheDocument()
  expect(fetchMock.mock.calls[0][0]).not.toContain(identity.cpf)
  rerender(<FacialEnrollment token="token" {...identity} email="other@example.test" role="employee" onReady={ready} onUnauthenticated={vi.fn()} />)
  await waitFor(() => expect(ready).toHaveBeenLastCalledWith(null))
})

test('stages then captures with multipart and exposes only a successful enrollment proof', async () => {
  const stage = { session_id: 'session', status: 'awaiting_capture', result_code: 'capture_required', expires_at: '2999-01-01T00:00:00Z' }
  const fetchMock = vi.fn()
    .mockResolvedValueOnce({ ok: true, json: async () => ({ ...enabled, person_id: null, status: 'missing_or_revoked', revision: 0 }) })
    .mockResolvedValueOnce({ ok: true, json: async () => stage })
    .mockResolvedValueOnce({ ok: true, json: async () => ({ ...stage, status: 'ready', result_code: 'enrollment_ready' }) })
  vi.stubGlobal('fetch', fetchMock)
  const ready = vi.fn()
  render(<FacialEnrollment token="token" {...identity} role="client" onReady={ready} onUnauthenticated={vi.fn()} />)
  fireEvent.click(screen.getByRole('button', { name: 'Verificar cadastro facial' }))
  fireEvent.click(await screen.findByRole('button', { name: 'Captura de teste' }))
  expect(await screen.findByText(/Captura validada/)).toBeInTheDocument()
  expect(ready).toHaveBeenLastCalledWith({ binding: personBinding(identity.email, identity.cpf), sessionId: 'session', expiresAt: stage.expires_at })
  expect(fetchMock.mock.calls[2][1].body).toBeInstanceOf(FormData)
  expect(fetchMock.mock.calls[2][1].headers).not.toHaveProperty('Content-Type')
})

test('replacement and revocation use the displayed revision and keep ordinary login separate', async () => {
  const fetchMock = vi.fn().mockResolvedValueOnce({ ok: true, json: async () => enabled })
    .mockResolvedValueOnce({ ok: true, json: async () => ({ ...enabled, status: 'missing_or_revoked', revision: 2, cleanup_pending: true }) })
  vi.stubGlobal('fetch', fetchMock)
  vi.spyOn(window, 'confirm').mockReturnValue(true)
  render(<FacialEnrollment token="token" {...identity} personId="person" role="employee" onUnauthenticated={vi.fn()} />)
  fireEvent.click(screen.getByRole('button', { name: 'Verificar cadastro facial' }))
  fireEvent.click(await screen.findByRole('button', { name: 'Revogar rosto' }))
  expect(await screen.findByText(/Cadastro facial revogado/)).toBeInTheDocument()
  expect(JSON.parse(fetchMock.mock.calls[1][1].body)).toMatchObject({ expected_revision: 1 })
  expect(window.confirm).toHaveBeenCalledWith(expect.stringContaining('O login continuará disponível'))
  vi.restoreAllMocks()
})
