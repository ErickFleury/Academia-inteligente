import { cleanup, fireEvent, render, screen, within } from '@testing-library/react'
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


test('searches names and opens full details without exposing internal metadata', async () => {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, json: async () => [
    { id: 'one', name: 'Esteira', description: 'Descrição completa', active_quantity: 2, image_url: null, brand: 'SEGREDO', serial_number: 'SERIAL-PRIVADO' },
    { id: 'two', name: 'Leg press', description: null, active_quantity: 1, image_url: null },
  ] }))
  render(<EquipmentCatalogPage />)
  await screen.findByRole('heading', { name: 'Leg press' })
  fireEvent.change(screen.getByRole('textbox', { name: 'Buscar equipamento' }), { target: { value: 'esteira' } })
  expect(screen.queryByRole('heading', { name: 'Leg press' })).not.toBeInTheDocument()
  fireEvent.click(screen.getByRole('button', { name: 'Ver detalhes de Esteira' }))
  const dialog = await screen.findByRole('dialog', { name: 'Esteira' })
  expect(within(dialog).getByText('Descrição completa')).toBeInTheDocument()
  expect(screen.queryByText('SEGREDO')).not.toBeInTheDocument()
  expect(screen.queryByText('SERIAL-PRIVADO')).not.toBeInTheDocument()
})

test('offers retry after catalog failure and keeps broken photos readable', async () => {
  vi.stubGlobal('fetch', vi.fn().mockRejectedValueOnce(new Error()).mockResolvedValue({ ok: true, json: async () => [{ id: 'one', name: 'Esteira', description: null, active_quantity: 1, image_url: '/missing.jpg' }] }))
  render(<EquipmentCatalogPage />)
  fireEvent.click(await screen.findByRole('button', { name: 'Tentar novamente' }))
  fireEvent.error(await screen.findByAltText('Imagem de Esteira'))
  expect(screen.getByText('Imagem indisponível')).toBeInTheDocument()
  expect(screen.getByRole('button', { name: 'Ver detalhes de Esteira' })).toBeEnabled()
})
