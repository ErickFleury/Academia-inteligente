import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter, useLocation } from 'react-router-dom'
import { afterEach, expect, test, vi } from 'vitest'

import type { Session } from '../auth'
import { SessionContext } from '../session-context'
import { AreaSwitch } from './area-switch'

afterEach(cleanup)

function session(roles: string[]): Session {
  return { accessToken: 'same-token', refreshToken: 'same-refresh', expiresAt: Date.now() + 300_000, lastActivityAt: Date.now(), roles }
}

function Path() {
  return <output aria-label="Rota atual">{useLocation().pathname}</output>
}

test.each([[], ['client'], ['instructor'], ['employee'], ['admin']])('hides switching without both active roles: %j', (...roles) => {
  render(<SessionContext.Provider value={session(roles)}><AreaSwitch area="instructor" /></SessionContext.Provider>)
  expect(screen.queryByRole('link')).not.toBeInTheDocument()
  expect(screen.queryByText('Área atual')).not.toBeInTheDocument()
})

test('switches to the explicit client entry without changing the session', () => {
  const current = session(['client', 'instructor'])
  const onNavigate = vi.fn()
  render(<SessionContext.Provider value={current}><MemoryRouter initialEntries={['/instrutor/feed']}><AreaSwitch area="instructor" onNavigate={onNavigate} /><Path /></MemoryRouter></SessionContext.Provider>)
  expect(screen.getByText('Área do instrutor')).toBeInTheDocument()
  const link = screen.getByRole('link', { name: 'Mudar para a área do cliente' })
  expect(link).toHaveAttribute('href', '/cliente')
  fireEvent.click(link)
  expect(screen.getByLabelText('Rota atual')).toHaveTextContent('/cliente')
  expect(onNavigate).toHaveBeenCalledOnce()
  expect(current.accessToken).toBe('same-token')
  expect(current.roles).toEqual(['client', 'instructor'])
})

test('switches back to instructor Feed and reacts to removal of a role', () => {
  const renderSwitch = (roles: string[]) => <SessionContext.Provider value={session(roles)}><MemoryRouter><AreaSwitch area="client" /><Path /></MemoryRouter></SessionContext.Provider>
  const view = render(renderSwitch(['client', 'instructor']))
  expect(screen.getByText('Área do cliente')).toBeInTheDocument()
  fireEvent.click(screen.getByRole('link', { name: 'Mudar para a área do instrutor' }))
  expect(screen.getByLabelText('Rota atual')).toHaveTextContent('/instrutor/feed')
  view.rerender(renderSwitch(['client']))
  expect(screen.queryByRole('link')).not.toBeInTheDocument()
})
