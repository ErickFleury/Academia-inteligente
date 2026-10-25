import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, expect, test, vi } from 'vitest'

import { developmentAccepted, developmentSaved } from '../prescription-development-fixtures'
import type { PrescriptionOutcome, PrescriptionReason } from '../training-prescription'
import { TrainingPrescriptionReview } from './training-prescription-review'

afterEach(cleanup)

test('renders exactly the backend projection and session scope with separate instructor review', async () => {
  const submit = vi.fn().mockResolvedValue(undefined)
  render(<TrainingPrescriptionReview role="client" outcome={developmentAccepted} onSubmit={submit} />)
  expect(screen.getByRole('table', { name: 'Ficha de exercícios' })).toHaveTextContent('Agachamento (Dia A)23–52–3 RIR30 s')
  expect(screen.getByText(/não representa a semana inteira/)).toBeInTheDocument()
  expect(screen.getByText(/a ficha ainda não está aprovada nem ativa/)).toBeInTheDocument()
  expect(screen.queryByRole('region', { name: 'Fundamentação das decisões' })).not.toBeInTheDocument()
  fireEvent.click(screen.getByRole('button', { name: 'Enviar proposta para revisão do instrutor' }))
  await waitFor(() => expect(submit).toHaveBeenCalledWith('rascunho-ficticio', 1))
  expect(await screen.findByRole('status')).toHaveTextContent('ainda não está aprovada')
})

test.each(['restriction_conflict', 'missing_input', 'insufficient_support', 'technical_unavailability'] as const)('rejected %s has no workout or submission action', (category: PrescriptionReason) => {
  const rejected: PrescriptionOutcome = { status: 'rejected', category, reason_codes: ['raw_internal'], message: 'Raw provider internals must not appear' }
  render(<TrainingPrescriptionReview role="client" outcome={rejected} onSubmit={vi.fn()} />)
  expect(screen.getByRole('alert')).toBeInTheDocument()
  expect(screen.queryByRole('table')).not.toBeInTheDocument()
  expect(screen.queryByRole('button', { name: /Enviar proposta/ })).not.toBeInTheDocument()
  expect(screen.queryByText(/Raw provider/)).not.toBeInTheDocument()
})

test.each(['missing_input', 'insufficient_support', 'technical_unavailability'] as const)('%s never declares that the student cannot exercise', (category) => {
  render(<TrainingPrescriptionReview role="client" outcome={{ status: 'rejected', category, message: '', reason_codes: [] }} />)
  expect(screen.getByRole('alert').textContent).not.toMatch(/não pode treinar|perigoso|conflita com uma restrição/)
})

test('clearly separates preserved earlier content from the discarded candidate', () => {
  render(<TrainingPrescriptionReview role="client" savedDraft={developmentSaved} outcome={{ status: 'rejected', category: 'insufficient_support', message: '', reason_codes: [] }} />)
  expect(screen.getByRole('region', { name: 'Rascunho salvo anterior' })).toHaveTextContent('preservado após a tentativa sem sucesso')
  expect(screen.getByRole('table')).toHaveTextContent('Elevação de panturrilha')
  expect(screen.queryByRole('button', { name: /Enviar/ })).not.toBeInTheDocument()
})

test('shows decision-to-rule and source locators only for the instructor', () => {
  render(<TrainingPrescriptionReview role="instructor" outcome={developmentAccepted} />)
  expect(screen.getByRole('region', { name: 'Fundamentação das decisões' })).toHaveTextContent('regra-ficticia-volume')
  expect(screen.getByText(/Decisão: Agachamento — Séries e repetições/)).toBeInTheDocument()
})

test('manual assumption requires a saved draft, instructor, reason and exact revision', async () => {
  const assume = vi.fn().mockResolvedValue(undefined)
  const { rerender } = render(<TrainingPrescriptionReview role="client" savedDraft={developmentSaved} onAssumeManual={assume} />)
  expect(screen.queryByRole('button', { name: 'Assumir responsabilidade manual' })).not.toBeInTheDocument()
  rerender(<TrainingPrescriptionReview role="instructor" onAssumeManual={assume} />)
  expect(screen.queryByRole('button', { name: 'Assumir responsabilidade manual' })).not.toBeInTheDocument()
  rerender(<TrainingPrescriptionReview role="instructor" savedDraft={developmentSaved} onAssumeManual={assume} />)
  expect(screen.getByRole('button', { name: 'Assumir responsabilidade manual' })).toBeDisabled()
  fireEvent.change(screen.getByRole('textbox', { name: 'Motivo da responsabilidade manual' }), { target: { value: 'Revisão profissional' } })
  fireEvent.click(screen.getByRole('button', { name: 'Assumir responsabilidade manual' }))
  await waitFor(() => expect(assume).toHaveBeenCalledWith(developmentSaved.id, 2, 'Revisão profissional'))
  expect(screen.getByRole('button', { name: 'Assumir responsabilidade manual' })).toBeDisabled()
})

test('confirmation is explicit and invalidates when the effective snapshot changes', async () => {
  const confirm = vi.fn().mockResolvedValue(undefined)
  const facts = [{ id: 'goal', label: 'Objetivo', value: 'Exemplo fictício' }]
  const { rerender } = render(<TrainingPrescriptionReview role="client" confirmation={{ snapshotHash: 'first', facts }} onConfirm={confirm} />)
  expect(screen.getByRole('button', { name: 'Confirmar informações' })).toBeDisabled()
  fireEvent.click(screen.getByRole('checkbox'))
  fireEvent.click(screen.getByRole('button', { name: 'Confirmar informações' }))
  await waitFor(() => expect(confirm).toHaveBeenCalledWith('first'))
  rerender(<TrainingPrescriptionReview role="client" confirmation={{ snapshotHash: 'second', facts }} onConfirm={confirm} />)
  expect(screen.getByRole('checkbox')).not.toBeChecked()
  expect(screen.getByRole('button', { name: 'Confirmar informações' })).toBeDisabled()
})

test('loading disables actions and a failed stale action gives reload feedback', async () => {
  const submit = vi.fn().mockRejectedValue(new Error('internal_revision_mismatch'))
  const { rerender } = render(<TrainingPrescriptionReview role="client" outcome={developmentAccepted} loading onSubmit={submit} />)
  expect(screen.getByRole('button', { name: /Enviar proposta/ })).toBeDisabled()
  expect(screen.getByRole('progressbar')).toBeInTheDocument()
  rerender(<TrainingPrescriptionReview role="client" outcome={developmentAccepted} onSubmit={submit} />)
  fireEvent.click(screen.getByRole('button', { name: /Enviar proposta/ }))
  expect(await screen.findByRole('status')).toHaveTextContent('Recarregue os dados')
  expect(screen.queryByText(/internal_revision/)).not.toBeInTheDocument()
})
