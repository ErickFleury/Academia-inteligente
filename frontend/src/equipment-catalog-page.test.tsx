import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, expect, test, vi } from 'vitest'

import { EquipmentCatalogPage } from './equipment-catalog-page'

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

test('shows active equipment totals without implying real-time availability', async () => {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
    ok: true,
    json: async () => [{
      id: 'leg-press-45', name: 'Leg Press 45°', description: 'Plataforma inclinada.',
      image_url: '/images/leg-press.jpg', active_quantity: 4,
    }],
  }))

  render(<EquipmentCatalogPage />)

  expect(await screen.findByRole('heading', { name: 'Leg Press 45°' })).toBeInTheDocument()
  expect(screen.getByText('4 unidades ativas')).toBeInTheDocument()
  expect(screen.getByAltText('Imagem de Leg Press 45°')).toHaveAttribute('src', '/images/leg-press.jpg')
  expect(screen.getByText(/não indicam uso ou disponibilidade/i)).toBeInTheDocument()
})
