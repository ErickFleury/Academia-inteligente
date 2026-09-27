import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, expect, test, vi } from 'vitest'

import { ClientManagement } from './client-management'

const client = { id: '1', name: 'Ada Lovelace', first_name: 'Ada', surname: 'Lovelace', email: 'ada@example.test', cpf: '52998224725', phone: '11998765432', postal_code: '01001000', street: 'Praça da Sé', number: '1', complement: null, neighborhood: 'Sé', city: 'São Paulo', state: 'SP', client_active: true, identity_provisioned: false, created_at: '2026-09-20T00:00:00+00:00' }
afterEach(() => { cleanup(); vi.unstubAllGlobals() })

test('registers complete client data', async () => {
  const fetchMock = vi.fn().mockResolvedValueOnce({ ok: true, json: async () => [] }).mockResolvedValueOnce({ ok: true, json: async () => client }).mockResolvedValueOnce({ ok: true, json: async () => [client] })
  vi.stubGlobal('fetch', fetchMock)
  render(<ClientManagement accessToken="admin-token" onUnauthenticated={vi.fn()} />)
  await screen.findByText('Nenhum cliente encontrado.')
  for (const [label, value] of [['Nome', 'Ada'], ['Sobrenome', 'Lovelace'], ['E-mail', 'ada@example.test'], ['CPF', '529.982.247-25'], ['Telefone', '(11) 99876-5432'], ['CEP', '01001-000'], ['Logradouro', 'Praça da Sé'], ['Número', '1'], ['Bairro', 'Sé'], ['Cidade', 'São Paulo'], ['UF', 'SP']] as const) fireEvent.change(screen.getByRole('textbox', { name: label }), { target: { value } })
  fireEvent.click(screen.getByRole('button', { name: 'Cadastrar cliente' }))
  expect(await screen.findByText('Cliente cadastrado. Provisionamento de acesso pendente.')).toBeInTheDocument()
  expect(JSON.parse(fetchMock.mock.calls[1][1].body)).toMatchObject({ first_name: 'Ada', cpf: '529.982.247-25' })
})

test('keeps manual address entry available if CEP lookup fails', async () => {
  const fetchMock = vi.fn().mockResolvedValueOnce({ ok: true, json: async () => [] }).mockResolvedValueOnce({ ok: false, json: async () => ({ detail: 'CEP lookup is unavailable' }) })
  vi.stubGlobal('fetch', fetchMock)
  render(<ClientManagement accessToken="admin-token" onUnauthenticated={vi.fn()} />)
  await screen.findByText('Nenhum cliente encontrado.')
  fireEvent.change(screen.getByRole('textbox', { name: 'CEP' }), { target: { value: '01001-000' } })
  fireEvent.click(screen.getByRole('button', { name: 'Buscar CEP' }))
  expect(await screen.findByText('Não foi possível consultar o CEP. Preencha o endereço manualmente.')).toBeInTheDocument()
  fireEvent.change(screen.getByRole('textbox', { name: 'Logradouro' }), { target: { value: 'Rua Manual' } })
  expect(screen.getByRole('textbox', { name: 'Logradouro' })).toHaveValue('Rua Manual')
})

test('shows a specific Portuguese CPF validation message', async () => {
  const fetchMock = vi.fn().mockResolvedValueOnce({ ok: true, json: async () => [] }).mockResolvedValueOnce({ ok: false, status: 422, json: async () => ({ detail: 'A valid CPF is required' }) })
  vi.stubGlobal('fetch', fetchMock)
  render(<ClientManagement accessToken="admin-token" onUnauthenticated={vi.fn()} />)
  await screen.findByText('Nenhum cliente encontrado.')
  for (const [label, value] of [['Nome', 'Ada'], ['Sobrenome', 'Lovelace'], ['E-mail', 'ada@example.test'], ['CPF', '111.111.111-11'], ['Telefone', '(11) 99876-5432'], ['CEP', '01001-000'], ['Logradouro', 'Praça da Sé'], ['Número', '1'], ['Bairro', 'Sé'], ['Cidade', 'São Paulo'], ['UF', 'SP']] as const) fireEvent.change(screen.getByRole('textbox', { name: label }), { target: { value } })
  fireEvent.click(screen.getByRole('button', { name: 'Cadastrar cliente' }))
  expect(await screen.findByText('Informe um CPF válido.')).toBeInTheDocument()
})

test('edits profile data and client-only active state', async () => {
  const inactive = { ...client, surname: 'Byron', name: 'Ada Byron', client_active: false }
  const fetchMock = vi.fn().mockResolvedValueOnce({ ok: true, json: async () => [client] }).mockResolvedValueOnce({ ok: true, json: async () => client }).mockResolvedValueOnce({ ok: true, json: async () => inactive })
  vi.stubGlobal('fetch', fetchMock)
  render(<ClientManagement accessToken="admin-token" onUnauthenticated={vi.fn()} />)
  fireEvent.click(await screen.findByRole('button', { name: /ada lovelace/i }))
  await screen.findByRole('heading', { name: 'Editar cliente' })
  fireEvent.change(screen.getAllByRole('textbox', { name: 'Sobrenome' })[1], { target: { value: 'Byron' } })
  fireEvent.click(screen.getByRole('switch', { name: 'Cliente ativo' }))
  fireEvent.click(screen.getByRole('button', { name: 'Salvar alterações' }))
  await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(3))
  expect(JSON.parse(fetchMock.mock.calls[2][1].body)).toMatchObject({ surname: 'Byron', client_active: false })
  expect(screen.getByText('Inativo')).toBeInTheDocument()
})
