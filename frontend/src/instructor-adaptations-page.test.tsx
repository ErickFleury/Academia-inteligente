import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, expect, test, vi } from 'vitest'

import { InstructorAdaptationsPage } from './instructor-adaptations-page'

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

test('shows the active catalog model as inventory context in instructor review', async () => {
  vi.stubGlobal('fetch', vi.fn((url: string) => {
    if (url.endsWith('/equipment')) {
      return Promise.resolve({
        ok: true,
        json: async () => [{
          id: 'leg-press-45', name: 'Leg Press 45°', description: null,
          image_url: null, active_quantity: 4,
        }],
      })
    }
    return Promise.resolve({
      ok: true,
      json: async () => [{
        id: 'proposal-1', status: 'pending_instructor_review', source_client_request_id: 'request-1',
        explanation: 'Proposta para revisão.', reason: 'Quero uma alternativa.',
        base_items: [{ position: 1, exercise_name: 'Agachamento', sets: 3, repetitions: '8', load_guidance: 'Confortável', rest_seconds: 90 }],
        operations: [{
          operation_type: 'replace', target_position: 1, exercise_name: 'Leg Press 45°', sets: 3,
          repetitions: '10', load_guidance: 'Confortável', rest_seconds: 90,
          equipment_requirement: 'Leg Press 45°', equipment_model_id: 'leg-press-45',
          equipment_model_name: 'Leg Press 45°', is_existing_exercise: false,
        }],
      }],
    })
  }))

  render(<InstructorAdaptationsPage accessToken="access-token" onSignOut={vi.fn()} />)

  await screen.findByLabelText('Equipamento do catálogo (opcional)')
  const equipmentField = screen.getByRole('combobox', { name: 'Equipamento do catálogo (opcional)' })
  expect(equipmentField).toHaveTextContent('Leg Press 45°')
  expect(screen.getByText(/Unidades ativas indicam inventário do catálogo, não uso imediato/)).toBeInTheDocument()
  fireEvent.mouseDown(equipmentField)
  expect(await screen.findByRole('option', { name: 'Leg Press 45° — 4 unidades ativas' })).toBeInTheDocument()
  expect(screen.queryByText(/disponível|livre/i)).not.toBeInTheDocument()
})
