import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, expect, test, vi } from 'vitest'

import { AdminDashboard } from './admin-dashboard-page'

afterEach(() => { cleanup(); vi.unstubAllGlobals() })

function successfulDashboardFetch() {
  return vi.fn((url: string) => {
    if (url.endsWith('/active-clients')) return Promise.resolve({ ok: true, json: async () => ({ active_clients: 14 }) })
    if (url.endsWith('/attendance')) return Promise.resolve({ ok: true, json: async () => ({ weeks: [{ week_start: '2026-09-21', confirmed_entries: 7 }] }) })
    return Promise.resolve({ ok: true, json: async () => ({ occupancy: 3, status: 'current', updated_at: '2026-09-25T12:00:00Z' }) })
  })
}

test('shows non-identifying administrative indicators in Portuguese', async () => {
  vi.stubGlobal('fetch', successfulDashboardFetch())
  render(<AdminDashboard accessToken="access-token" onUnauthenticated={vi.fn()} />)

  expect(await screen.findByText('14')).toBeInTheDocument()
  expect(screen.getByText('3')).toBeInTheDocument()
  expect(screen.getByText('Entradas confirmadas por semana')).toBeInTheDocument()
  expect(screen.getByText('7')).toBeInTheDocument()
  expect(screen.getByText(/Não representa clientes únicos/)).toBeInTheDocument()
  expect(screen.queryByText(/cliente-1|referência|biometr/i)).not.toBeInTheDocument()
})

test('keeps successful indicators visible when attendance fails and retries only that indicator', async () => {
  const fetchMock = vi.fn()
    .mockResolvedValueOnce({ ok: true, json: async () => ({ active_clients: 2 }) })
    .mockResolvedValueOnce({ ok: false, status: 503, json: async () => ({ detail: 'Frequência indisponível.' }) })
    .mockResolvedValueOnce({ ok: true, json: async () => ({ occupancy: 1, status: 'stale', updated_at: null }) })
    .mockResolvedValueOnce({ ok: true, json: async () => ({ weeks: [{ week_start: '2026-09-21', confirmed_entries: 4 }] }) })
  vi.stubGlobal('fetch', fetchMock)
  render(<AdminDashboard accessToken="access-token" onUnauthenticated={vi.fn()} />)

  expect(await screen.findByText('Frequência indisponível.')).toBeInTheDocument()
  expect(screen.getByText('2')).toBeInTheDocument()
  expect(screen.getByText('1')).toBeInTheDocument()
  expect(screen.getByText(/Última contagem conhecida/)).toBeInTheDocument()
  fireEvent.click(screen.getByRole('button', { name: 'Tentar novamente' }))
  expect(await screen.findByText('4')).toBeInTheDocument()
})

test('ends the session when an administrative indicator is unauthenticated', async () => {
  const onUnauthenticated = vi.fn()
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: false, status: 401, json: async () => ({ detail: 'Unauthenticated' }) }))
  render(<AdminDashboard accessToken="expired-token" onUnauthenticated={onUnauthenticated} />)

  expect(await screen.findAllByText('Unauthenticated')).toHaveLength(3)
  expect(onUnauthenticated).toHaveBeenCalled()
})
