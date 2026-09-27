import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, expect, test, vi } from 'vitest'

import { EmployeeManagement } from './employee-management'

const employee = { id: '1', name: 'Maria Silva', first_name: 'Maria', surname: 'Silva', email: 'maria@example.test', cpf: '52998224725', phone: '11998765432', postal_code: '01001000', street: 'Praça da Sé', number: '1', complement: null, neighborhood: 'Sé', city: 'São Paulo', state: 'SP', cnpj: null, specialization: 'instructor', employee_active: true, identity_provisioned: false, created_at: '2026-09-27T00:00:00+00:00' }

afterEach(() => { cleanup(); vi.unstubAllGlobals() })

test('employee not found feedback is not confused with CEP lookup', async () => {
  vi.stubGlobal('fetch', vi.fn()
    .mockResolvedValueOnce({ ok: true, json: async () => [employee] })
    .mockResolvedValueOnce({ ok: false, status: 404, json: async () => ({ detail: 'Employee not found' }) }))
  render(<EmployeeManagement accessToken="admin-token" onUnauthenticated={vi.fn()} />)
  fireEvent.click(await screen.findByRole('button', { name: /Maria Silva/ }))
  expect(await screen.findByText('Instrutor não encontrado. Atualize a lista e tente novamente.')).toBeInTheDocument()
  expect(screen.queryByText(/CEP não encontrado/)).not.toBeInTheDocument()
})

test.each([404, 503])('CEP failure %s preserves manual values and does not claim provisioning failure', async (status) => {
  vi.stubGlobal('fetch', vi.fn()
    .mockResolvedValueOnce({ ok: true, json: async () => [] })
    .mockResolvedValueOnce({ ok: false, status, json: async () => ({ detail: 'Lookup failed' }) }))
  render(<EmployeeManagement accessToken="admin-token" onUnauthenticated={vi.fn()} />)
  await screen.findByText('Nenhum instrutor encontrado.')
  fireEvent.change(screen.getByRole('textbox', { name: 'CEP' }), { target: { value: '01001000' } })
  fireEvent.change(screen.getByRole('textbox', { name: 'Logradouro' }), { target: { value: 'Rua manual' } })
  fireEvent.click(screen.getByRole('button', { name: 'Buscar CEP' }))
  expect(await screen.findByText(/Preencha o endereço manualmente/)).toBeInTheDocument()
  expect(screen.getByRole('textbox', { name: 'Logradouro' })).toHaveValue('Rua manual')
  expect(screen.queryByText(/Sincronização de acesso pendente/)).not.toBeInTheDocument()
})

test('invalid edits retain inputs and show Portuguese validation feedback', async () => {
  vi.stubGlobal('fetch', vi.fn()
    .mockResolvedValueOnce({ ok: true, json: async () => [employee] })
    .mockResolvedValueOnce({ ok: true, json: async () => employee })
    .mockResolvedValueOnce({ ok: false, status: 422, json: async () => ({ detail: 'A valid CPF is required' }) }))
  render(<EmployeeManagement accessToken="admin-token" onUnauthenticated={vi.fn()} />)
  fireEvent.click(await screen.findByRole('button', { name: /Maria Silva/ }))
  await screen.findByRole('heading', { name: 'Editar instrutor' })
  fireEvent.change(screen.getAllByRole('textbox', { name: 'CPF' })[1], { target: { value: '00000000000' } })
  fireEvent.click(screen.getByRole('button', { name: 'Salvar alterações' }))
  expect(await screen.findByText(/Verifique os dados informados/)).toBeInTheDocument()
  expect(screen.getAllByRole('textbox', { name: 'CPF' })[1]).toHaveValue('00000000000')
  expect(screen.queryByText('A valid CPF is required')).not.toBeInTheDocument()
})

test('shows a controlled list failure and ends the loading state', async () => {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: false, status: 500, json: async () => ({}) }))
  render(<EmployeeManagement accessToken="admin-token" onUnauthenticated={vi.fn()} />)
  expect(screen.getByText('Carregando instrutores')).toBeInTheDocument()
  expect(await screen.findByText('Não foi possível carregar instrutores.')).toBeInTheDocument()
  expect(screen.queryByText('Carregando instrutores')).not.toBeInTheDocument()
})

test('registers an instructor with complete personal data', async () => {
  const fetchMock = vi.fn().mockResolvedValueOnce({ ok: true, json: async () => [] }).mockResolvedValueOnce({ ok: true, json: async () => ({ person_id: "person", status: "enabled", revision: 1, cleanup_pending: false }) }).mockResolvedValueOnce({ ok: true, json: async () => employee }).mockResolvedValueOnce({ ok: true, json: async () => [employee] })
  vi.stubGlobal('fetch', fetchMock)
  render(<EmployeeManagement accessToken="admin-token" onUnauthenticated={vi.fn()} />)
  await screen.findByText('Nenhum instrutor encontrado.')
  for (const [label, value] of [['Nome', 'Maria'], ['Sobrenome', 'Silva'], ['E-mail', 'maria@example.test'], ['CPF', '529.982.247-25'], ['Telefone', '(11) 99876-5432'], ['CEP', '01001-000'], ['Logradouro', 'Praça da Sé'], ['Número', '1'], ['Bairro', 'Sé'], ['Cidade', 'São Paulo'], ['UF', 'SP']] as const) fireEvent.change(screen.getByRole('textbox', { name: label }), { target: { value } })
  fireEvent.click(screen.getByRole('button', { name: 'Verificar cadastro facial' }))
  await screen.findByText(/será reutilizado/)
  fireEvent.click(screen.getByRole('button', { name: 'Cadastrar instrutor' }))
  expect(await screen.findByText('Instrutor cadastrado. Provisionamento de acesso pendente.')).toBeInTheDocument()
  expect(JSON.parse(fetchMock.mock.calls[2][1].body)).toMatchObject({ specialization: 'instructor', cpf: '529.982.247-25' })
})

test('keeps failed role updates visible and offers a shared-account retry', async () => {
  const ready = { ...employee, identity_provisioned: true }
  const pending = { ...employee, employee_active: false }
  const fetchMock = vi.fn()
    .mockResolvedValueOnce({ ok: true, json: async () => [ready] })
    .mockResolvedValueOnce({ ok: true, json: async () => ready })
    .mockResolvedValueOnce({ ok: false, status: 503, json: async () => ({ detail: 'Employee identity provisioning is pending' }) })
    .mockResolvedValueOnce({ ok: true, json: async () => pending })
    .mockResolvedValueOnce({ ok: true, json: async () => [pending] })
    .mockResolvedValueOnce({ ok: true, json: async () => ({ ...pending, identity_provisioned: true }) })
  vi.stubGlobal('fetch', fetchMock)
  render(<EmployeeManagement accessToken="admin-token" onUnauthenticated={vi.fn()} />)
  fireEvent.click(await screen.findByRole('button', { name: /Maria Silva/ }))
  await screen.findByRole('heading', { name: 'Editar instrutor' })
  fireEvent.click(screen.getByRole('switch', { name: 'Instrutor ativo' }))
  fireEvent.click(screen.getByRole('button', { name: 'Salvar alterações' }))
  expect(await screen.findByText(/Sincronização de acesso pendente/)).toBeInTheDocument()
  expect(screen.getByRole('switch', { name: 'Instrutor ativo' })).not.toBeChecked()
  fireEvent.click(screen.getByRole('button', { name: 'Provisionar acesso' }))
  expect(await screen.findByText('Acesso do instrutor sincronizado.')).toBeInTheDocument()
  expect(screen.queryByText(/recebeu as instruções/)).not.toBeInTheDocument()
})

test('shows immediate processing and prevents duplicate provisioning while the adapter is pending', async () => {
  let resolve!: (value: unknown) => void
  const pending = new Promise((done) => { resolve = done })
  const fetchMock = vi.fn().mockResolvedValueOnce({ ok: true, json: async () => [employee] }).mockResolvedValueOnce({ ok: true, json: async () => employee }).mockImplementationOnce(() => pending)
  vi.stubGlobal('fetch', fetchMock)
  render(<EmployeeManagement accessToken="token" onUnauthenticated={vi.fn()}/>)
  fireEvent.click(await screen.findByRole('button', {name:/Maria Silva/}))
  const provision = await screen.findByRole('button', {name:'Provisionar acesso'})
  fireEvent.click(provision)
  expect(screen.getByText('Salvando dados e sincronizando acesso do instrutor')).toBeInTheDocument()
  expect(provision).toBeDisabled()
  expect(provision).toHaveTextContent('Sincronizando...')
  fireEvent.click(provision)
  expect(fetchMock).toHaveBeenCalledTimes(3)
  resolve({ok:true,json:async()=>({...employee,identity_provisioned:true})})
  await screen.findByText('Acesso do instrutor sincronizado.')
})
