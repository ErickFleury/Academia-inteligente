import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, expect, test, vi } from 'vitest'

import { ClientManagement } from './client-management'

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

test('creates a client and refreshes the administrative list', async () => {
  const fetchMock = vi
    .fn()
    .mockResolvedValueOnce({ ok: true, json: async () => [] })
    .mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        id: '1',
        name: 'Ada Lovelace',
        email: 'ada@example.test',
        account_active: true,
        created_at: '2026-09-20T00:00:00+00:00',
      }),
    })
    .mockResolvedValueOnce({
      ok: true,
      json: async () => [
        {
          id: '1',
          name: 'Ada Lovelace',
          email: 'ada@example.test',
          account_active: true,
          created_at: '2026-09-20T00:00:00+00:00',
        },
      ],
    })
  vi.stubGlobal('fetch', fetchMock)

  render(<ClientManagement accessToken="admin-token" onUnauthenticated={vi.fn()} />)
  await screen.findByText('Nenhum cliente encontrado.')
  fireEvent.change(screen.getByRole('textbox', { name: /^nome/i }), {
    target: { value: 'Ada Lovelace' },
  })
  fireEvent.change(screen.getByRole('textbox', { name: /^e-mail/i }), {
    target: { value: 'ada@example.test' },
  })
  fireEvent.click(screen.getByRole('button', { name: 'Cadastrar cliente' }))

  expect(await screen.findByText('Cliente cadastrado com sucesso.')).toBeInTheDocument()
  await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(3))
  expect(fetchMock.mock.calls[1][0]).toBe('http://localhost:8000/clients')
  expect(fetchMock.mock.calls[1][1]).toMatchObject({
    method: 'POST',
    headers: { Authorization: 'Bearer admin-token' },
  })
  expect(screen.getByText('Ada Lovelace — ada@example.test (Ativo)')).toBeInTheDocument()
})

test('searches by name or e-mail and shows an API validation message', async () => {
  const fetchMock = vi
    .fn()
    .mockResolvedValueOnce({ ok: true, json: async () => [] })
    .mockResolvedValueOnce({
      ok: true,
      json: async () => [
        {
          id: '1',
          name: 'Grace Hopper',
          email: 'grace@example.test',
          account_active: true,
          created_at: '2026-09-20T00:00:00+00:00',
        },
      ],
    })
    .mockResolvedValueOnce({
      ok: false,
      json: async () => ({ detail: 'An account already uses this e-mail address' }),
    })
  vi.stubGlobal('fetch', fetchMock)

  render(<ClientManagement accessToken="admin-token" onUnauthenticated={vi.fn()} />)
  await screen.findByText('Nenhum cliente encontrado.')
  fireEvent.change(screen.getByRole('textbox', { name: /^pesquisar por nome ou e-mail/i }), {
    target: { value: 'grace@example' },
  })
  fireEvent.click(screen.getByRole('button', { name: 'Pesquisar' }))

  expect(await screen.findByText('Grace Hopper — grace@example.test (Ativo)')).toBeInTheDocument()
  expect(fetchMock.mock.calls[1][0]).toBe('http://localhost:8000/clients?query=grace%40example')
  fireEvent.change(screen.getByRole('textbox', { name: /^e-mail/i }), {
    target: { value: 'duplicate@example.test' },
  })
  fireEvent.change(screen.getByRole('textbox', { name: /^nome/i }), {
    target: { value: 'Grace Hopper' },
  })
  fireEvent.click(screen.getByRole('button', { name: 'Cadastrar cliente' }))

  expect(await screen.findByText('An account already uses this e-mail address')).toBeInTheDocument()
})

test('updates a selected client profile and deactivates its application account', async () => {
  const client = {
    id: '1',
    name: 'Ada Lovelace',
    email: 'ada@example.test',
    account_active: true,
    created_at: '2026-09-20T00:00:00+00:00',
  }
  const fetchMock = vi
    .fn()
    .mockResolvedValueOnce({ ok: true, json: async () => [client] })
    .mockResolvedValueOnce({ ok: true, json: async () => client })
    .mockResolvedValueOnce({
      ok: true,
      json: async () => ({ ...client, name: 'Ada Byron', account_active: false }),
    })
  vi.stubGlobal('fetch', fetchMock)

  render(<ClientManagement accessToken="admin-token" onUnauthenticated={vi.fn()} />)
  const selectedButton = await screen.findByRole('button', {
    name: 'Ada Lovelace — ada@example.test (Ativo)',
  })
  fireEvent.click(selectedButton)
  await screen.findByRole('heading', { name: 'Editar cliente' })
  fireEvent.change(screen.getByRole('textbox', { name: /^nome do cliente/i }), {
    target: { value: 'Ada Byron' },
  })
  fireEvent.click(screen.getByRole('switch', { name: 'Conta ativa' }))
  fireEvent.click(screen.getByRole('button', { name: 'Salvar alterações' }))

  expect(await screen.findByText('Cliente atualizado com sucesso.')).toBeInTheDocument()
  expect(fetchMock.mock.calls[2][0]).toBe('http://localhost:8000/clients/1')
  expect(JSON.parse(fetchMock.mock.calls[2][1].body)).toEqual({
    name: 'Ada Byron',
    email: 'ada@example.test',
    account_active: false,
  })
  expect(screen.getByText('Ada Byron — ada@example.test (Inativo)')).toBeInTheDocument()
})

test('offers identity reconciliation for a legacy client', async () => {
  const client = {
    id: 'legacy', name: 'Legacy Client', email: 'legacy@example.test', account_active: true,
    identity_provisioned: false, created_at: '2026-09-20T00:00:00+00:00',
  }
  const fetchMock = vi
    .fn()
    .mockResolvedValueOnce({ ok: true, json: async () => [client] })
    .mockResolvedValueOnce({ ok: true, json: async () => client })
    .mockResolvedValueOnce({ ok: true, json: async () => ({ ...client, identity_provisioned: true }) })
  vi.stubGlobal('fetch', fetchMock)

  render(<ClientManagement accessToken="admin-token" onUnauthenticated={vi.fn()} />)
  fireEvent.click(await screen.findByRole('button', { name: /legacy client/i }))
  await screen.findByRole('heading', { name: 'Editar cliente' })
  fireEvent.click(screen.getByRole('button', { name: 'Provisionar acesso' }))

  expect(await screen.findByText(/acesso do cliente provisionado/i)).toBeInTheDocument()
  expect(fetchMock.mock.calls[2][0]).toBe('http://localhost:8000/clients/legacy/provision-identity')
})

test('sends an onboarding invitation only for a provisioned active client', async () => {
  const client = {
    id: 'client-1', name: 'Ada Lovelace', email: 'ada@example.test', account_active: true,
    identity_provisioned: true, created_at: '2026-09-20T00:00:00+00:00',
  }
  const fetchMock = vi
    .fn()
    .mockResolvedValueOnce({ ok: true, json: async () => [client] })
    .mockResolvedValueOnce({ ok: true, json: async () => client })
    .mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        id: 'invitation-1', delivery_status: 'sent', expires_at: '2026-09-21T00:00:00+00:00',
        sent_at: '2026-09-20T00:00:00+00:00',
      }),
    })
  vi.stubGlobal('fetch', fetchMock)

  render(<ClientManagement accessToken="admin-token" onUnauthenticated={vi.fn()} />)
  fireEvent.click(await screen.findByRole('button', { name: /ada lovelace/i }))
  await screen.findByRole('heading', { name: 'Editar cliente' })
  fireEvent.click(screen.getByRole('button', { name: 'Enviar convite de onboarding' }))

  expect(await screen.findByText('Convite de onboarding enviado. Expira em 24 horas.')).toBeInTheDocument()
  expect(fetchMock.mock.calls[2][0]).toBe('http://localhost:8000/onboarding/clients/client-1/invitations')
  expect(fetchMock.mock.calls[2][1]).toMatchObject({
    method: 'POST', headers: { Authorization: 'Bearer admin-token' },
  })
})
