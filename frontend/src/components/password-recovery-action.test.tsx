import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, expect, test, vi } from 'vitest'

import { PasswordRecoveryAction } from './password-recovery-action'

afterEach(() => { cleanup(); vi.unstubAllGlobals() })

test.each([undefined, 'client-1'])('sends an authenticated recovery request with no credentials for %s', async (clientId) => {
  let resolve!: (value: unknown) => void
  const fetch = vi.fn(() => new Promise((done) => { resolve = done }))
  vi.stubGlobal('fetch', fetch)
  render(<PasswordRecoveryAction accessToken="test-token" clientId={clientId} />)
  fireEvent.click(screen.getByRole('button', { name: 'Redefinir senha' }))
  const pending = screen.getByRole('button', { name: 'Enviando link…' })
  expect(pending).toBeDisabled()
  fireEvent.click(pending)
  expect(fetch).toHaveBeenCalledTimes(1)
  expect(fetch).toHaveBeenCalledWith(`http://localhost:8000${clientId ? '/clients/client-1/password-reset' : '/identity/me/password-reset'}`, {
    method: 'POST', headers: { Authorization: 'Bearer test-token' },
  })
  resolve({ ok: true })
  expect(await screen.findByText(/E-mail de redefinição enviado/)).toBeInTheDocument()
  expect(screen.getByRole('button', { name: 'Redefinir senha' })).toBeDisabled()
  expect(screen.queryByRole('textbox')).not.toBeInTheDocument()
})

test.each([401, 403, 409, 429, 503])('shows controlled Portuguese feedback for failure %s', async (status) => {
  vi.stubGlobal('fetch', vi.fn(async () => ({ ok: false, status })))
  render(<PasswordRecoveryAction accessToken="test-token" />)
  fireEvent.click(screen.getByRole('button', { name: 'Redefinir senha' }))
  await waitFor(() => expect(screen.getByRole('alert')).toBeInTheDocument())
  expect(screen.queryByText(/E-mail de redefinição enviado/)).not.toBeInTheDocument()
})

test('network failures do not expose raw error details', async () => {
  vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('Internal network detail')))
  render(<PasswordRecoveryAction accessToken="test-token" />)
  fireEvent.click(screen.getByRole('button', { name: 'Redefinir senha' }))
  expect(await screen.findByText(/Não foi possível confirmar o envio/)).toBeInTheDocument()
  expect(screen.queryByText('Internal network detail')).not.toBeInTheDocument()
})
