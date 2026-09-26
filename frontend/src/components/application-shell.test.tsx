import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, expect, test, vi } from 'vitest'

import { AdminShell, ClientShell } from './application-shell'

afterEach(cleanup)

test.each([
  ['administração', AdminShell],
  ['área do cliente', ClientShell],
])('the Sair button in %s submits logout exactly once', (_area, Shell) => {
  const onSignOut = vi.fn()
  render(<Shell onSignOut={onSignOut}>Conteúdo protegido</Shell>)

  const button = screen.getByRole('button', { name: 'Sair' })
  fireEvent.click(button)
  fireEvent.click(button)

  expect(onSignOut).toHaveBeenCalledOnce()
  expect(button).toBeDisabled()
  expect(screen.getByRole('button', { name: 'Saindo…' })).toBeDisabled()
})
