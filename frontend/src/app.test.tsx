import { render, screen } from '@testing-library/react'
import { expect, test } from 'vitest'

import { App } from './app'

test('renders the foundation application shell', () => {
  render(<App />)

  expect(screen.getByRole('heading', { name: 'Academia Inteligente' })).toBeInTheDocument()
})
