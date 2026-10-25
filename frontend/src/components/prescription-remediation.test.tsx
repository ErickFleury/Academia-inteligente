import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { useState } from 'react'
import { afterEach, expect, test, vi } from 'vitest'
import { developmentAccepted } from '../prescription-development-fixtures'
import type { DoseDetails } from '../training-dose'
import type { RequestInputRequirements } from '../training-prescription'
import { PrescriptionRequestInputs } from './prescription-request-inputs'
import { TrainingModalityFields } from './training-modality-fields'
import { TrainingPrescriptionReview } from './training-prescription-review'

afterEach(() => { cleanup(); vi.unstubAllGlobals() })

test('failed bounds identify the exact exercise and approved open limits in Portuguese', () => {
  render(<TrainingPrescriptionReview role="client" outcome={{ status: 'rejected', category: 'insufficient_support', message: '', reason_codes: ['parameter_outside_policy'], issues: [{ position: 2, field: 'repetitions', reason: 'parameter_outside_policy', allowed: { minimum: 15, maximum: null, minimum_inclusive: false, maximum_inclusive: true } }] }} />)
  expect(screen.getByText(/Exercício 2: Repetições precisa de correção; permitido: mais de 15/)).toBeInTheDocument()
  expect(screen.queryByText(/parameter_outside_policy/)).not.toBeInTheDocument()
  expect(screen.queryByRole('table')).not.toBeInTheDocument()
})

test('continuous exercise and owner basis survive review without invented zero rest or sets', () => {
  const outcome = structuredClone(developmentAccepted)
  if (outcome.status !== 'accepted') throw new Error('accepted fixture required')
  outcome.prescription.approval_basis = 'owner_decision'
  outcome.prescription.professional_review_performed = false
  Object.assign(outcome.prescription.projection.items[0], { sets: null, rest_seconds: null, repetitions: '10 min', dose_details: { mode: 'aerobic', dose: { kind: 'aerobic', minutes: '10', intensity: 'moderate' }, rest: { kind: 'not_applicable', seconds: null } } })
  render(<TrainingPrescriptionReview role="client" outcome={outcome} />)
  expect(screen.getByRole('table')).toHaveTextContent('10 min')
  expect(screen.getByRole('table')).toHaveTextContent('Não se aplica')
  expect(screen.getByRole('table')).not.toHaveTextContent('0 s')
  expect(screen.getByText(/sem parecer profissional/i)).toBeInTheDocument()
})

test('modality edit preserves structured dose instead of writing resistance fields', () => {
  const initial: DoseDetails = { mode: 'aerobic', dose: { kind: 'aerobic', minutes: '10', intensity: 'moderate', observation_fact: 'reported_talk_test' }, rest: { kind: 'not_applicable', seconds: null } }
  function Form() {
    const [details, setDetails] = useState(initial)
    return <><TrainingModalityFields details={details} index={0} onChange={setDetails} /><output>{JSON.stringify(details)}</output></>
  }
  render(<Form />)
  fireEvent.change(screen.getByRole('spinbutton', { name: 'Duração em minutos 1' }), { target: { value: '12.5' } })
  expect(JSON.parse(screen.getByRole('status').textContent!)).toMatchObject({ dose: { minutes: '12.5', observation_fact: 'reported_talk_test' }, rest: { kind: 'not_applicable', seconds: null } })
  expect(screen.queryByLabelText(/Séries/)).not.toBeInTheDocument()
})

test('request collection requires an explicit observation and attestation and hides instructor-only inputs', async () => {
  const fetch = vi.fn().mockResolvedValue({ ok: true })
  vi.stubGlobal('fetch', fetch)
  const onSaved = vi.fn()
  const requirements: RequestInputRequirements = { snapshot_hash: 'a'.repeat(64), requirements: [
    { key: 'observed_control', label: 'Controle observado', source: 'request', can_provide: true, value: null, value_type: 'boolean' },
    { key: 'baseline_capacity', label: 'Medição do instrutor', source: 'request', can_provide: false, value: null, value_type: 'number' },
  ] }
  render(<PrescriptionRequestInputs accessToken="scoped-token" requirements={requirements} onSaved={onSaved} />)
  expect(screen.queryByLabelText('Medição do instrutor')).not.toBeInTheDocument()
  expect(screen.getByRole('button', { name: 'Registrar informações' })).toBeDisabled()
  fireEvent.mouseDown(screen.getByRole('combobox', { name: 'Controle observado' }))
  fireEvent.click(screen.getByRole('option', { name: 'Não' }))
  expect(screen.getByRole('button', { name: 'Registrar informações' })).toBeDisabled()
  fireEvent.click(screen.getByRole('checkbox'))
  fireEvent.click(screen.getByRole('button', { name: 'Registrar informações' }))
  await waitFor(() => expect(onSaved).toHaveBeenCalledOnce())
  const [url, request] = fetch.mock.calls[0]
  expect(url).toMatch(/\/training\/prescription\/inputs$/)
  expect(request.headers.Authorization).toBe('Bearer scoped-token')
  expect(JSON.parse(request.body)).toEqual({ expected_snapshot_hash: 'a'.repeat(64), values: { observed_control: { value: false } } })
})
