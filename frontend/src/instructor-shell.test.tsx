import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, expect, test, vi } from 'vitest'

import { InstructorShell } from './instructor-shell'
import { SessionContext } from './session-context'

afterEach(() => { cleanup(); vi.unstubAllGlobals() })

function renderShell(onSignOut = vi.fn()) {
  return render(
    <MemoryRouter initialEntries={['/instrutor/feed']}>
      <InstructorShell onSignOut={onSignOut}>Conteúdo do instrutor</InstructorShell>
    </MemoryRouter>,
  )
}

test('places the exact instructor navigation in the shared sidebar without client features', () => {
  const fetchMock = vi.fn()
  vi.stubGlobal('fetch', fetchMock)
  renderShell()

  const sidebar = screen.getByRole('complementary')
  const navigation = within(sidebar).getByRole('navigation', { name: 'Navegação da área do instrutor' })
  expect(within(navigation).getAllByRole('link').map((link) => link.textContent)).toEqual([
    'Feed', 'Planos pendentes', 'Meus planos', 'Todos os planos', 'Clientes', 'Equipamentos', 'Perfil',
  ])
  expect(within(navigation).getByRole('link', { name: 'Feed' })).toHaveAttribute('aria-current', 'page')
  expect(within(sidebar).getByRole('button', { name: 'Sair' })).toBeInTheDocument()
  expect(screen.getByRole('main')).toHaveTextContent('Conteúdo do instrutor')
  expect(sidebar).not.toContainElement(screen.getByRole('main'))
  expect(screen.queryByRole('link', { name: 'Meu treino' })).not.toBeInTheDocument()
  expect(screen.queryByRole('link', { name: 'Abrir meu perfil' })).not.toBeInTheDocument()
  expect(fetchMock).not.toHaveBeenCalled()
})

test('mobile navigation closes after selection and updates the active destination', async () => {
  renderShell()
  const trigger = screen.getByRole('button', { name: 'Abrir navegação' })
  expect(trigger).toHaveAttribute('aria-controls', 'navegacao-instrutor-movel')
  expect(trigger).toHaveAttribute('aria-expanded', 'false')
  fireEvent.click(trigger)
  expect(trigger).toHaveAttribute('aria-expanded', 'true')
  const navigation = screen.getByRole('navigation', { name: 'Navegação da área do instrutor' })
  expect(navigation).toHaveAttribute('id', 'navegacao-instrutor-movel')
  fireEvent.click(within(navigation).getByRole('link', { name: 'Perfil' }))
  await waitFor(() => expect(screen.queryByRole('button', { name: 'Fechar navegação' })).not.toBeInTheDocument())
  expect(trigger).toHaveAttribute('aria-expanded', 'false')
  expect(screen.getByRole('link', { name: 'Perfil' })).toHaveAttribute('aria-current', 'page')
  expect(screen.getByRole('link', { name: 'Feed' })).not.toHaveAttribute('aria-current')
})

test('mobile navigation supports explicit close and Escape', async () => {
  renderShell()
  const trigger = screen.getByRole('button', { name: 'Abrir navegação' })
  fireEvent.click(trigger)
  fireEvent.click(screen.getByRole('button', { name: 'Fechar navegação' }))
  await waitFor(() => expect(trigger).toHaveAttribute('aria-expanded', 'false'))
  fireEvent.click(trigger)
  fireEvent.keyDown(screen.getByRole('button', { name: 'Fechar navegação' }), { key: 'Escape', code: 'Escape' })
  await waitFor(() => expect(trigger).toHaveAttribute('aria-expanded', 'false'))
})

test('instructor sidebar signs out only once', () => {
  const onSignOut = vi.fn()
  renderShell(onSignOut)
  const button = screen.getByRole('button', { name: 'Sair' })
  fireEvent.click(button)
  fireEvent.click(button)
  expect(onSignOut).toHaveBeenCalledOnce()
  expect(screen.getByRole('button', { name: 'Saindo…' })).toBeDisabled()
})

test('dual-role mobile switch stays outside the menu and closes the drawer', async () => {
  render(<SessionContext.Provider value={{ accessToken: 'same-token', refreshToken: 'refresh', expiresAt: Date.now() + 300_000, lastActivityAt: Date.now(), roles: ['client', 'instructor'] }}><MemoryRouter initialEntries={['/instrutor/feed']}><InstructorShell onSignOut={vi.fn()}>Conteúdo</InstructorShell></MemoryRouter></SessionContext.Provider>)
  const navigation = screen.getByRole('navigation', { name: 'Navegação da área do instrutor' })
  expect(within(navigation).getAllByRole('link')).toHaveLength(7)
  expect(navigation).not.toContainElement(screen.getByRole('link', { name: 'Mudar para a área do cliente' }))
  const trigger = screen.getByRole('button', { name: 'Abrir navegação' })
  fireEvent.click(trigger)
  fireEvent.click(screen.getByRole('link', { name: 'Mudar para a área do cliente' }))
  await waitFor(() => expect(trigger).toHaveAttribute('aria-expanded', 'false'))
})
