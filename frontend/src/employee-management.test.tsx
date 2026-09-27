import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, expect, test, vi } from 'vitest'

import { EmployeeManagement } from './employee-management'

const employee = { id: '1', name: 'Maria Silva', first_name: 'Maria', surname: 'Silva', email: 'maria@example.test', cpf: '52998224725', phone: '11998765432', postal_code: '01001000', street: 'Praça da Sé', number: '1', complement: null, neighborhood: 'Sé', city: 'São Paulo', state: 'SP', cnpj: null, specialization: 'instructor', employee_active: true, identity_provisioned: false, created_at: '2026-09-27T00:00:00+00:00' }

afterEach(() => { cleanup(); vi.unstubAllGlobals() })

test('registers an instructor with complete personal data', async () => {
  const fetchMock = vi.fn().mockResolvedValueOnce({ ok: true, json: async () => [] }).mockResolvedValueOnce({ ok: true, json: async () => employee }).mockResolvedValueOnce({ ok: true, json: async () => [employee] })
  vi.stubGlobal('fetch', fetchMock)
  render(<EmployeeManagement accessToken="admin-token" onUnauthenticated={vi.fn()} />)
  await screen.findByText('Nenhum instrutor encontrado.')
  for (const [label, value] of [['Nome', 'Maria'], ['Sobrenome', 'Silva'], ['E-mail', 'maria@example.test'], ['CPF', '529.982.247-25'], ['Telefone', '(11) 99876-5432'], ['CEP', '01001-000'], ['Logradouro', 'Praça da Sé'], ['Número', '1'], ['Bairro', 'Sé'], ['Cidade', 'São Paulo'], ['UF', 'SP']] as const) fireEvent.change(screen.getByRole('textbox', { name: label }), { target: { value } })
  fireEvent.click(screen.getByRole('button', { name: 'Cadastrar instrutor' }))
  expect(await screen.findByText('Instrutor cadastrado. Provisionamento de acesso pendente.')).toBeInTheDocument()
  expect(JSON.parse(fetchMock.mock.calls[1][1].body)).toMatchObject({ specialization: 'instructor', cpf: '529.982.247-25' })
})
