import { cleanup, render, screen, within } from '@testing-library/react'
import { afterEach, expect, test, vi } from 'vitest'
import { OccupancyPage } from './occupancy-page'

afterEach(() => { cleanup(); vi.unstubAllGlobals() })

test('shows only the anonymous current occupancy count', async () => {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, json: async () => ({ occupancy: 4, status: 'current', updated_at: '2026-09-25T12:00:00Z' }) }))
  render(<OccupancyPage onSignOut={vi.fn()} />)
  expect(await screen.findByRole('heading', { name: 'Clientes presentes' })).toBeInTheDocument()
  expect(within(screen.getByRole('main')).getByText('4')).toBeInTheDocument(); expect(screen.getByText('clientes presentes')).toBeInTheDocument()
  expect(screen.getByText(/Contagem atualizada/)).toBeInTheDocument()
  expect(screen.queryByText(/referência|evento|cliente-/i)).not.toBeInTheDocument()
})

test('marks the preserved count as stale', async () => {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, json: async () => ({ occupancy: 2, status: 'stale', updated_at: '2026-09-25T12:00:00Z' }) }))
  render(<OccupancyPage onSignOut={vi.fn()} />)
  expect(await within(screen.getByRole('main')).findByText('2')).toBeInTheDocument()
  expect(screen.getByText(/Última contagem conhecida/)).toBeInTheDocument()
})
