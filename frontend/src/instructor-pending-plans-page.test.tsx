import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, expect, test, vi } from 'vitest'

import { InstructorPendingPlansPage } from './instructor-pending-plans-page'

const plan = {
  id: 'draft', plan_id: 'plan', version_number: 1, revision: 1,
  client_name: 'Maria Silva', source: 'adaptation', name: 'Força', objective: 'Ganhar força',
  created_at: '2026-09-27T12:00:00Z', updated_at: '2026-09-27T12:00:00Z',
  current_responsible_instructor_name: 'João Silva',
  items: [{ exercise_name: 'Leg Press', sets: 3, repetitions: '8', load_guidance: 'Confortável', rest_seconds: 90, equipment_model_id: 'machine', equipment_requirement: 'Leg Press 45°' }],
}
const ok = (body: unknown) => ({ ok: true, json: async () => body })
function mount() { render(<MemoryRouter><InstructorPendingPlansPage accessToken="token" onSignOut={vi.fn()} /></MemoryRouter>) }
afterEach(() => { cleanup(); vi.unstubAllGlobals() })

function mockFetch(action?: (url: string, init?: RequestInit) => unknown) {
  const fetchMock = vi.fn(async (url: string, init?: RequestInit) => {
    if (url.includes('/usable-models?')) return ok({ items: [{ id: 'machine', name: 'Leg Press 45°' }], next_cursor: null })
    const result = action?.(url, init)
    if (result) return result
    if (url.includes('/pending?')) return ok({ items: [plan], next_offset: null })
    return ok(plan)
  })
  vi.stubGlobal('fetch', fetchMock)
  return fetchMock
}

test('lists minimized pending metadata and approves directly with the viewed revision', async () => {
  const fetchMock = mockFetch()
  mount()
  expect(await screen.findByRole('button', { name: 'Revisar plano de Maria Silva' })).toBeInTheDocument()
  expect(screen.getByText(/Adaptação aceita pelo cliente/)).toBeInTheDocument()
  expect(screen.getByText(/Instrutor responsável pelo treino atual: João Silva/)).toBeInTheDocument()
  fireEvent.click(screen.getByRole('button', { name: 'Revisar plano de Maria Silva' }))
  fireEvent.click(await screen.findByRole('button', { name: 'Aprovar' }))
  expect(await screen.findByText('Plano aprovado e definido como treino atual.')).toBeInTheDocument()
  await waitFor(() => expect(screen.getByRole('heading', { name: 'Aguardando revisão' })).toHaveFocus())
  const request = fetchMock.mock.calls.find(([url]) => url.endsWith('/approve'))!
  expect(JSON.parse(request[1]!.body as string)).toEqual({ expected_revision: 1 })
  expect(fetchMock.mock.calls.some(([url]) => /instructor-decision|\/activate/.test(url))).toBe(false)
})

test('edits the whole draft, preserves equipment, and saving never activates', async () => {
  const fetchMock = mockFetch((_, init) => {
    if (init?.method !== 'PATCH') return undefined
    const input = JSON.parse(init.body as string)
    return ok({ ...plan, ...input, revision: input.expected_revision + 1 })
  })
  mount()
  fireEvent.click(await screen.findByRole('button', { name: 'Revisar plano de Maria Silva' }))
  await screen.findByRole('heading', { name: 'Revisar plano de Maria Silva' })
  fireEvent.click(screen.getByRole('tab', { name: 'Editar rascunho' }))
  expect(screen.getByRole('combobox', { name: 'Equipamento do catálogo 1' })).toHaveTextContent('Leg Press 45°')
  await waitFor(() => expect(screen.getByRole('combobox', { name: 'Equipamento do catálogo 1' })).not.toHaveAttribute('aria-disabled', 'true'))
  fireEvent.mouseDown(screen.getByRole('combobox', { name: 'Equipamento do catálogo 1' }))
  expect(await screen.findByRole('option', { name: 'Leg Press 45°' })).toBeInTheDocument()
  fireEvent.click(screen.getByRole('option', { name: 'Leg Press 45°' }))
  fireEvent.change(screen.getByLabelText(/Nome do plano/), { target: { value: 'Força revisada' } })
  fireEvent.change(screen.getByLabelText(/Descanso em segundos 1/), { target: { value: '120' } })
  fireEvent.click(screen.getByRole('button', { name: 'Salvar rascunho' }))
  expect(await screen.findByText('Rascunho salvo. O treino atual não foi alterado.')).toBeInTheDocument()
  const patch = fetchMock.mock.calls.find(([, init]) => init?.method === 'PATCH')!
  expect(JSON.parse(patch[1]!.body as string)).toMatchObject({ name: 'Força revisada', expected_revision: 1, items: [{ rest_seconds: 120, equipment_model_id: 'machine' }] })
  expect(fetchMock.mock.calls.some(([url]) => url.endsWith('/approve'))).toBe(false)
  fireEvent.click(screen.getByRole('button', { name: 'Aprovar alterações' }))
  await screen.findByText('Plano aprovado e definido como treino atual.')
  expect(JSON.parse(fetchMock.mock.calls.find(([url]) => url.endsWith('/approve'))![1]!.body as string)).toEqual({ expected_revision: 3 })
})

test('stale save blocks approval until the draft has been reloaded', async () => {
  const fetchMock = mockFetch((_, init) => init?.method === 'PATCH' ? { ok: false, status: 409 } : undefined)
  mount()
  fireEvent.click(await screen.findByRole('button', { name: 'Revisar plano de Maria Silva' }))
  await screen.findByRole('heading', { name: 'Revisar plano de Maria Silva' })
  fireEvent.click(screen.getByRole('tab', { name: 'Editar rascunho' }))
  fireEvent.click(screen.getByRole('button', { name: 'Aprovar alterações' }))
  await screen.findByText('Este rascunho mudou. Recarregue e revise antes de continuar.')
  expect(screen.getByRole('button', { name: 'Aprovar alterações' })).toBeDisabled()
  expect(fetchMock.mock.calls.some(([url]) => url.endsWith('/approve'))).toBe(false)
  fireEvent.click(screen.getByRole('button', { name: 'Recarregar rascunho' }))
  await waitFor(() => expect(screen.getByRole('button', { name: 'Aprovar' })).not.toBeDisabled())
})

test('loading failure is visible and retry can reach an empty state', async () => {
  let fail = true
  mockFetch((url) => url.includes('/pending?') ? (fail ? { ok: false, status: 503 } : ok({ items: [], next_offset: null })) : undefined)
  mount()
  expect(screen.getByText('Carregando planos pendentes')).toBeInTheDocument()
  await screen.findByText('Não foi possível concluir a revisão. Tente novamente.')
  expect(screen.queryByText('Carregando planos pendentes')).not.toBeInTheDocument()
  fail = false
  fireEvent.click(screen.getByRole('button', { name: 'Recarregar lista' }))
  expect(await screen.findByText('Nenhum plano pendente')).toBeInTheDocument()
})

test('loads another bounded page without replacing the existing list', async () => {
  mockFetch((url) => url.includes('/pending?') ? ok(url.endsWith('offset=20') ? { items: [{ ...plan, id: 'other', client_name: 'Outro cliente' }], next_offset: null } : { items: [plan], next_offset: 20 }) : undefined)
  mount()
  fireEvent.click(await screen.findByRole('button', { name: 'Carregar mais planos' }))
  expect(await screen.findByRole('button', { name: 'Revisar plano de Outro cliente' })).toBeInTheDocument()
  expect(screen.getByRole('button', { name: 'Revisar plano de Maria Silva' })).toBeInTheDocument()
})


test('opens a readable preview before editing and preserves unsaved changes across preview', async () => {
  const fetchMock = mockFetch()
  mount()
  fireEvent.click(await screen.findByRole('button', { name: 'Revisar plano de Maria Silva' }))
  expect(await screen.findByRole('heading', { name: 'Leg Press' })).toBeInTheDocument()
  expect(screen.queryByLabelText(/Nome do plano/)).not.toBeInTheDocument()
  expect(fetchMock.mock.calls.some(([url]) => url.includes('/usable-models'))).toBe(false)
  fireEvent.click(screen.getByRole('tab', { name: 'Editar rascunho' }))
  fireEvent.change(screen.getByLabelText(/Nome do plano/), { target: { value: 'Treino ajustado' } })
  fireEvent.click(screen.getByRole('tab', { name: 'Visualizar treino' }))
  expect(screen.getByText('Treino ajustado')).toBeInTheDocument()
  expect(screen.getByText('Alterações não salvas')).toBeInTheDocument()
  fireEvent.click(screen.getByRole('button', { name: 'Fechar revisão' }))
  await screen.findByRole('dialog', { name: 'Descartar alterações não salvas?' })
  fireEvent.click(screen.getByRole('button', { name: 'Continuar editando' }))
  await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument())
  expect(screen.getByText('Treino ajustado')).toBeInTheDocument()
  fireEvent.click(screen.getByRole('button', { name: 'Fechar revisão' }))
  fireEvent.click(await screen.findByRole('button', { name: 'Descartar alterações' }))
  await waitFor(() => expect(screen.queryByRole('region', { name: 'Revisão do plano' })).not.toBeInTheDocument())
  expect(fetchMock.mock.calls.some(([, init]) => init?.method === 'PATCH' || init?.method === 'POST')).toBe(false)
  await waitFor(() => expect(screen.getByRole('button', { name: 'Revisar plano de Maria Silva' })).toHaveFocus())
})


test('approval from preview saves displayed unsaved edits before approving the new revision', async () => {
  const fetchMock = mockFetch((_, init) => {
    if (init?.method !== 'PATCH') return undefined
    return ok({ ...plan, ...JSON.parse(init.body as string), revision: 2 })
  })
  mount()
  fireEvent.click(await screen.findByRole('button', { name: 'Revisar plano de Maria Silva' }))
  await screen.findByRole('heading', { name: 'Leg Press' })
  fireEvent.click(screen.getByRole('tab', { name: 'Editar rascunho' }))
  fireEvent.change(screen.getByLabelText(/Nome do plano/), { target: { value: 'Treino revisado na prévia' } })
  fireEvent.click(screen.getByRole('tab', { name: 'Visualizar treino' }))
  fireEvent.click(screen.getByRole('button', { name: 'Aprovar alterações' }))
  await screen.findByText('Plano aprovado e definido como treino atual.')
  const writes = fetchMock.mock.calls.filter(([, init]) => init?.method === 'PATCH' || init?.method === 'POST')
  expect(writes.map(([, init]) => init?.method)).toEqual(['PATCH', 'POST'])
  expect(JSON.parse(writes[0][1]!.body as string)).toMatchObject({ name: 'Treino revisado na prévia', expected_revision: 1 })
  expect(JSON.parse(writes[1][1]!.body as string)).toEqual({ expected_revision: 2 })
})
