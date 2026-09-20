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
          created_at: '2026-09-20T00:00:00+00:00',
        },
      ],
    })
  vi.stubGlobal('fetch', fetchMock)

  render(<ClientManagement accessToken="admin-token" />)
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
  expect(screen.getByText('Ada Lovelace — ada@example.test')).toBeInTheDocument()
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
          created_at: '2026-09-20T00:00:00+00:00',
        },
      ],
    })
    .mockResolvedValueOnce({
      ok: false,
      json: async () => ({ detail: 'An account already uses this e-mail address' }),
    })
  vi.stubGlobal('fetch', fetchMock)

  render(<ClientManagement accessToken="admin-token" />)
  await screen.findByText('Nenhum cliente encontrado.')
  fireEvent.change(screen.getByRole('textbox', { name: /^pesquisar por nome ou e-mail/i }), {
    target: { value: 'grace@example' },
  })
  fireEvent.click(screen.getByRole('button', { name: 'Pesquisar' }))

  expect(await screen.findByText('Grace Hopper — grace@example.test')).toBeInTheDocument()
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
