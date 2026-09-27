import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, expect, test, vi } from 'vitest'
import { EquipmentEditor } from './equipment-editor'

const model = { id: 'saved', name: 'Esteira', active: true, active_quantity: 1, image_source: 'none', image_url: null, image_link: null }
afterEach(() => { cleanup(); vi.restoreAllMocks(); vi.unstubAllGlobals() })
test('photo failure retries against the saved model without duplicating registration', async () => {
  vi.stubGlobal('URL', class extends URL { static createObjectURL() { return 'blob:test' } static revokeObjectURL() {} })
  let photoFails = true
  const mock = vi.fn(async (_: string, init?: RequestInit) => init?.method === 'PUT' && photoFails ? { ok: false, status: 503, json: async () => ({}) } : { ok: true, json: async () => model })
  vi.stubGlobal('fetch', mock)
  const saved = vi.fn()
  render(<EquipmentEditor token="token" model={null} onClose={vi.fn()} onSaved={saved} />)
  fireEvent.change(screen.getByRole('textbox', { name: 'Nome do equipamento' }), { target: { value: 'Esteira' } })
  fireEvent.change(screen.getByLabelText('Escolher foto do equipamento'), { target: { files: [new File(['image'], 'photo.png', { type: 'image/png' })] } })
  fireEvent.click(screen.getByRole('button', { name: 'Continuar' }))
  fireEvent.click(screen.getByRole('button', { name: 'Cadastrar equipamento' }))
  await screen.findByText(/Equipamento e unidades salvos. A foto ainda não foi salva/)
  expect(saved).not.toHaveBeenCalled()
  photoFails = false
  fireEvent.click(screen.getByRole('button', { name: 'Salvar alterações' }))
  await waitFor(() => expect(saved).toHaveBeenCalledOnce())
  expect(mock.mock.calls.filter(([, init]) => init?.method === 'POST')).toHaveLength(1)
  expect(mock.mock.calls.filter(([, init]) => init?.method === 'PUT')).toHaveLength(2)
  expect(mock.mock.calls.some(([url, init]) => url.endsWith('/saved') && init?.method === 'PATCH')).toBe(true)
})

test('validates name and reports broken image preview before registration', async () => {
  vi.stubGlobal('fetch', vi.fn())
  render(<EquipmentEditor token="token" model={null} onClose={vi.fn()} onSaved={vi.fn()} />)
  fireEvent.click(screen.getByRole('button', { name: 'Continuar' }))
  expect(screen.getByText('Informe o nome do equipamento.')).toBeInTheDocument()
  fireEvent.click(screen.getByRole('tab', { name: 'Usar link' }))
  fireEvent.change(screen.getByRole('textbox', { name: 'Link da imagem' }), { target: { value: 'https://images.test/broken.jpg' } })
  fireEvent.error(await screen.findByAltText('Imagem de equipamento'))
  expect(screen.getByText('Imagem indisponível')).toBeInTheDocument()
  expect(fetch).not.toHaveBeenCalled()
})
