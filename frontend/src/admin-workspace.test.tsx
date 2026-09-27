import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, expect, test, vi } from 'vitest'
import { AdminWorkspace } from './admin-workspace'

afterEach(() => { cleanup(); vi.unstubAllGlobals() })

test('keeps indicators and both directories in separate accessible sections without losing a search draft', async () => {
  const fetchMock = vi.fn(async (url: string) => ({ ok: true, json: async () => url.endsWith('/active-clients') ? { active_clients: 12 } : url.endsWith('/attendance') ? { weeks: [] } : url.endsWith('/occupancy') ? { occupancy: 3, status: 'current', updated_at: null } : [] }))
  vi.stubGlobal('fetch', fetchMock)
  render(<AdminWorkspace accessToken="token" onUnauthenticated={vi.fn()} />)
  expect(await screen.findByText('12')).toBeInTheDocument()
  expect(screen.getByRole('tabpanel', { name: 'Visão geral' })).toBeVisible()
  expect(screen.queryByRole('button', { name: 'Novo cliente' })).not.toBeInTheDocument()
  fireEvent.click(screen.getByRole('tab', { name: 'Clientes' }))
  expect(screen.getByRole('tabpanel', { name: 'Clientes' })).toBeVisible()
  fireEvent.change(screen.getByRole('textbox', { name: 'Pesquisar por nome ou e-mail' }), { target: { value: 'Mariana' } })
  fireEvent.click(screen.getByRole('tab', { name: 'Instrutores' }))
  expect(screen.getByRole('button', { name: 'Novo instrutor' })).toBeVisible()
  expect(screen.queryByRole('button', { name: 'Novo cliente' })).not.toBeInTheDocument()
  fireEvent.click(screen.getByRole('tab', { name: 'Clientes' }))
  expect(screen.getByRole('textbox', { name: 'Pesquisar por nome ou e-mail' })).toHaveValue('Mariana')
  expect(fetchMock).toHaveBeenCalledTimes(5)
})
