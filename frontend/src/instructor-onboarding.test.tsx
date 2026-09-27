import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, expect, test, vi } from 'vitest'
import { OnboardingForm } from './onboarding-form'

const draft = { status: 'draft', completed_at: null, training_goal: 'Força', training_experience: 'beginner', height_cm: 170, weight_kg: '70.50', has_limitations_or_complaints: false, limitations_or_complaints: null, uses_medications: true, medications: 'Informação do cliente', has_health_conditions: false, health_conditions: null }
const ok = (body: unknown) => ({ ok: true, json: async () => body })
afterEach(() => { cleanup(); vi.unstubAllGlobals() })
function mount() { render(<MemoryRouter><OnboardingForm accessToken="token" onSignOut={vi.fn()} instructorClient={{ id: 'client', name: 'Ana Silva' }} onBack={vi.fn()} /></MemoryRouter>) }

test('completed instructor form stays editable and saves all fields on the target route', async () => {
  const completed = { ...draft, status: 'completed', completed_at: '2026-09-27T12:00:00Z' }
  const fetchMock = vi.fn(async (_url: string, init?: RequestInit) => ok(init?.method === 'PATCH' ? { ...completed, ...JSON.parse(init.body as string) } : completed))
  vi.stubGlobal('fetch', fetchMock); mount()
  await screen.findByRole('heading', { name: 'Onboarding de Ana Silva' })
  expect(screen.getByLabelText('Quais medicações você utiliza?')).not.toBeDisabled()
  expect(screen.queryByRole('link', { name: 'Responder por conversa' })).not.toBeInTheDocument()
  expect(screen.queryByRole('button', { name: 'Concluir onboarding' })).not.toBeInTheDocument()
  fireEvent.change(screen.getByLabelText('Quais medicações você utiliza?'), { target: { value: 'Nova informação' } })
  fireEvent.click(screen.getByRole('button', { name: 'Salvar alterações do onboarding' }))
  await screen.findByText('Onboarding atualizado com segurança.')
  const write = fetchMock.mock.calls.find(([, init]) => init?.method === 'PATCH')!
  expect(write[0]).toContain('/instructor/clients/client/onboarding')
  expect(JSON.parse(write[1]!.body as string)).toMatchObject({ medications: 'Nova informação', training_goal: 'Força' })
})

test('explicit completion first saves the displayed values and then completes', async () => {
  const fetchMock = vi.fn(async (_url: string, init?: RequestInit) => ok(init?.method === 'POST' ? { ...draft, status: 'completed', completed_at: '2026-09-27T12:00:00Z' } : draft))
  vi.stubGlobal('fetch', fetchMock); mount()
  fireEvent.click(await screen.findByRole('button', { name: 'Concluir onboarding' }))
  await screen.findByText('Onboarding concluído com sucesso.')
  expect(fetchMock.mock.calls.map(([, init]) => init?.method)).toEqual(['GET','PATCH','POST'])
  expect(fetchMock.mock.calls[2][0]).toContain('/onboarding/completion')
  expect(screen.getByRole('button', { name: 'Salvar alterações do onboarding' })).toBeEnabled()
})

test('failed save retains editable values and prevents completion', async () => {
  const fetchMock = vi.fn(async (_url: string, init?: RequestInit) => init?.method === 'PATCH' ? { ok: false, status: 422 } : ok(draft))
  vi.stubGlobal('fetch', fetchMock); mount()
  fireEvent.click(await screen.findByRole('button', { name: 'Concluir onboarding' }))
  await screen.findByText('Revise os campos obrigatórios e as informações de saúde antes de salvar ou concluir.')
  expect(fetchMock.mock.calls.some(([, init]) => init?.method === 'POST')).toBe(false)
  expect(screen.getByLabelText('Quais medicações você utiliza?')).toHaveValue('Informação do cliente')
})
