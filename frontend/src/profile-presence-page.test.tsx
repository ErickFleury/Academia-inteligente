import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, expect, test, vi } from 'vitest'

import { ProfilePresencePage } from './profile-presence-page'

vi.mock('./occupancy', () => ({ getOccupancy: async () => ({ occupancy: 0 }) }))

afterEach(() => { cleanup(); vi.unstubAllGlobals() })

test('shows the opt-in profile tag without turning the page into a presence directory', async () => {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, json: async () => ({ sharing_enabled: true, currently_present: true }) }))
  render(<ProfilePresencePage accessToken="token" onSignOut={vi.fn()} />)
  expect(await screen.findByText('Na academia')).toBeInTheDocument()
  expect(screen.getByRole('switch', { name: /Mostrar no meu perfil/ })).toBeChecked()
  expect(screen.queryByText(/clientes presentes/i)).not.toBeInTheDocument()
})

test('allows immediate revocation on a compact profile control', async () => {
  const fetchMock = vi.fn()
    .mockResolvedValueOnce({ ok: true, json: async () => ({ sharing_enabled: true, currently_present: true }) })
    .mockResolvedValueOnce({ ok: true, json: async () => ({ sharing_enabled: false, currently_present: false }) })
  vi.stubGlobal('fetch', fetchMock)
  render(<ProfilePresencePage accessToken="token" onSignOut={vi.fn()} />)
  const toggle = await screen.findByRole('switch', { name: /Mostrar no meu perfil/ })
  fireEvent.click(toggle)
  expect(await screen.findByText(/Desativá-la remove/)).toBeInTheDocument()
  expect(screen.queryByText('Na academia')).not.toBeInTheDocument()
  expect(fetchMock.mock.calls[1][1]).toMatchObject({ method: 'PATCH', body: JSON.stringify({ enabled: false }) })
})
