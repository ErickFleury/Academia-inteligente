import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, expect, test, vi } from 'vitest'
import { InstructorClientsPage } from './instructor-clients-page'

const client = { id: 'client', name: 'João Silva', onboarding_status: 'draft', draft_id: null, current_id: null, responsible_instructor_name: null }
const ok = (body: unknown) => ({ ok: true, json: async () => body })
afterEach(() => { cleanup(); vi.unstubAllGlobals() })
function setup(override?: (url: string, init?: RequestInit) => unknown) {
  const mock = vi.fn(async (url: string, init?: RequestInit) => {
    const result = override?.(url, init); if (result) return result
    if (url.endsWith('/equipment')) return ok([])
    if (url.includes('/responsible')) return ok({ items: [], next_cursor: null })
    if (url.includes('/clients?')) return ok({ items: [client], next_cursor: null })
    return ok(client)
  })
  vi.stubGlobal('fetch', mock)
  render(<MemoryRouter><InstructorClientsPage accessToken="token" onSignOut={vi.fn()} /></MemoryRouter>)
  return mock
}

test('offers exact filters and minimized workspace links for both draft and current', async () => {
  const fetchMock = setup((url) => url.endsWith('/client') ? ok({ ...client, draft_id: 'draft', current_id: 'current' }) : undefined)
  await screen.findByText('João Silva')
  fireEvent.change(screen.getByLabelText('Nome do cliente'), { target: { value: ' joao ' } })
  fireEvent.mouseDown(screen.getByRole('combobox', { name: 'Treino' }))
  expect(screen.queryByRole('option', { name: 'Somente rascunho' })).not.toBeInTheDocument()
  fireEvent.click(screen.getByRole('option', { name: 'Pendente de aprovação' }))
  fireEvent.click(screen.getByRole('button', { name: 'Pesquisar clientes' }))
  await waitFor(() => expect(fetchMock.mock.calls.some(([url]) => url.includes('search=joao') && url.includes('training=pending'))).toBe(true))
  fireEvent.click(screen.getByRole('button', { name: 'Abrir cliente' }))
  await screen.findByRole('heading', { name: 'Treinos de João Silva' })
  expect(screen.getByRole('link', { name: 'Abrir rascunho' })).toHaveAttribute('href', '/instrutor/planos-pendentes?rascunho=draft')
  expect(screen.getByRole('link', { name: 'Ver plano atual e histórico' })).toHaveAttribute('href', '/instrutor/todos-os-planos?plano=current')
  expect(screen.queryByRole('button', { name: 'Criar primeiro rascunho' })).not.toBeInTheDocument()
})

test('manual form uses the complete item schema, never approves, and locks on conflict', async () => {
  const fetchMock = setup((_, init) => init?.method === 'POST' ? { ok: false, status: 409 } : undefined)
  fireEvent.click(await screen.findByRole('button', { name: 'Abrir cliente' }))
  fireEvent.click(await screen.findByRole('button', { name: 'Criar primeiro rascunho' }))
  for (const [label, value] of [['Nome do plano','Força'], ['Objetivo','Ganhar força'], ['Nome do exercício 1','Agachamento'], ['Repetições 1','8'], ['Orientação de carga 1','Confortável']]) fireEvent.change(screen.getByLabelText(new RegExp(label)), { target: { value } })
  fireEvent.click(screen.getByRole('button', { name: 'Salvar primeiro rascunho' }))
  await screen.findByText('O cliente já possui um plano ou rascunho. Recarregue o cadastro para continuar.')
  const request = fetchMock.mock.calls.find(([, init]) => init?.method === 'POST')!
  expect(JSON.parse(request[1]!.body as string)).toMatchObject({ name: 'Força', items: [{ exercise_name: 'Agachamento', sets: 3 }] })
  expect(fetchMock.mock.calls.some(([url]) => url.includes('/approve'))).toBe(false)
  expect(screen.getByRole('button', { name: 'Salvar primeiro rascunho' })).toBeDisabled()
  fireEvent.click(screen.getByRole('button', { name: 'Recarregar cadastro' }))
  expect(await screen.findByRole('button', { name: 'Criar primeiro rascunho' })).not.toBeDisabled()
})

test('shows a controlled error and permits retry to an empty result', async () => {
  let fail = true
  setup((url) => url.includes('/clients?') ? fail ? { ok: false, status: 503 } : ok({ items: [], next_cursor: null }) : undefined)
  await screen.findByText('Não foi possível concluir a operação. Tente novamente.')
  fail = false
  fireEvent.click(screen.getByRole('button', { name: 'Recarregar lista' }))
  await screen.findByText('Nenhum cliente encontrado')
})
