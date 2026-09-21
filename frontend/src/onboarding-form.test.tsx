import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, expect, test, vi } from 'vitest'

import { OnboardingForm } from './onboarding-form'

const emptyDraft = {
  status: 'draft',
  completed_at: null,
  training_goal: null,
  training_experience: null,
  height_cm: null,
  weight_kg: null,
  has_limitations_or_complaints: null,
  limitations_or_complaints: null,
  uses_medications: null,
  medications: null,
  has_health_conditions: null,
  health_conditions: null,
}

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

test('loads the authenticated client draft and saves physical and health fields', async () => {
  const fetchMock = vi
    .fn()
    .mockResolvedValueOnce({ ok: true, json: async () => emptyDraft })
    .mockResolvedValueOnce({
      ok: true,
      json: async () => ({ ...emptyDraft, training_goal: 'Ganhar força', height_cm: 175 }),
    })
  vi.stubGlobal('fetch', fetchMock)

  render(<OnboardingForm accessToken="access-token" onSignOut={vi.fn()} />)

  expect(await screen.findByRole('heading', { name: 'Conte um pouco sobre você' })).toBeInTheDocument()
  expect(fetchMock.mock.calls[0][0]).toBe('http://localhost:8000/onboarding/me')
  expect(fetchMock.mock.calls[0][1]).toMatchObject({
    method: 'GET',
    headers: { Authorization: 'Bearer access-token' },
  })

  fireEvent.change(screen.getByLabelText('Qual é o seu objetivo de treino?'), {
    target: { value: 'Ganhar força' },
  })
  fireEvent.change(screen.getByLabelText('Altura'), { target: { value: '175' } })
  fireEvent.click(screen.getByRole('button', { name: 'Salvar rascunho' }))

  expect(await screen.findByText('Rascunho salvo com segurança.')).toBeInTheDocument()
  expect(fetchMock.mock.calls[1][0]).toBe('http://localhost:8000/onboarding/me')
  expect(fetchMock.mock.calls[1][1]).toMatchObject({ method: 'PATCH' })
  expect(JSON.parse(fetchMock.mock.calls[1][1].body)).toMatchObject({
    training_goal: 'Ganhar força',
    height_cm: 175,
  })
})

test('shows conditional health details only after the client answers yes', async () => {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, json: async () => emptyDraft }))

  render(<OnboardingForm accessToken="access-token" onSignOut={vi.fn()} />)

  await screen.findByRole('heading', { name: 'Conte um pouco sobre você' })
  expect(screen.queryByLabelText('Quais medicações você utiliza?')).not.toBeInTheDocument()
  fireEvent.mouseDown(screen.getByLabelText('Você utiliza alguma medicação?'))
  fireEvent.click(await screen.findByRole('option', { name: 'Sim' }))

  expect(screen.getByLabelText('Quais medicações você utiliza?')).toBeInTheDocument()
})

test('accepts only numeric physical input and normalizes a decimal comma before saving', async () => {
  const fetchMock = vi
    .fn()
    .mockResolvedValueOnce({ ok: true, json: async () => emptyDraft })
    .mockResolvedValueOnce({ ok: true, json: async () => emptyDraft })
  vi.stubGlobal('fetch', fetchMock)

  render(<OnboardingForm accessToken="access-token" onSignOut={vi.fn()} />)

  await screen.findByRole('heading', { name: 'Conte um pouco sobre você' })
  const height = screen.getByLabelText('Altura') as HTMLInputElement
  const weight = screen.getByLabelText('Peso') as HTMLInputElement
  fireEvent.change(height, { target: { value: '17e5' } })
  fireEvent.change(weight, { target: { value: '70,50' } })

  expect(height.value).toBe('')
  expect(weight.value).toBe('70,50')
  fireEvent.click(screen.getByRole('button', { name: 'Salvar rascunho' }))

  expect(await screen.findByText('Rascunho salvo com segurança.')).toBeInTheDocument()
  expect(JSON.parse(fetchMock.mock.calls[1][1].body)).toMatchObject({
    height_cm: null,
    weight_kg: '70.50',
  })
})

test('prevents incomplete completion and displays the completed state after the explicit action', async () => {
  const completeDraft = {
    ...emptyDraft,
    training_goal: 'Ganhar força', training_experience: 'beginner', height_cm: 170,
    weight_kg: '70.50', has_limitations_or_complaints: false,
    uses_medications: false, has_health_conditions: false,
  }
  const fetchMock = vi.fn()
    .mockResolvedValueOnce({ ok: true, json: async () => completeDraft })
    .mockResolvedValueOnce({ ok: true, json: async () => ({ ...completeDraft, status: 'completed', completed_at: '2026-09-21T12:00:00Z' }) })
  vi.stubGlobal('fetch', fetchMock)

  render(<OnboardingForm accessToken="access-token" onSignOut={vi.fn()} />)
  expect(await screen.findByRole('button', { name: 'Concluir onboarding' })).toBeEnabled()
  fireEvent.click(screen.getByRole('button', { name: 'Concluir onboarding' }))
  expect(await screen.findByText('Seu onboarding foi concluído com sucesso.')).toBeInTheDocument()
  expect(fetchMock.mock.calls[1][0]).toBe('http://localhost:8000/onboarding/me/completion')
  expect(fetchMock.mock.calls[1][1]).toMatchObject({ method: 'POST' })
})
