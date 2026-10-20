import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, expect, test, vi } from 'vitest'

import { EquipmentPhoto } from './equipment-presentation'

afterEach(() => { cleanup(); vi.unstubAllEnvs(); vi.unstubAllGlobals() })

test('offline mode blocks remote images while retaining local uploads', async () => {
  vi.stubEnv('VITE_ALLOW_EXTERNAL_IMAGES', 'false')
  const fetchMock = vi.fn()
  vi.stubGlobal('fetch', fetchMock)
  const view = render(<EquipmentPhoto url="https://images.example.test/photo.png" name="Banco" />)
  expect(screen.queryByRole('img')).not.toBeInTheDocument()
  expect(screen.getByText('Imagem indisponível')).toBeInTheDocument()
  expect(fetchMock).not.toHaveBeenCalled()
  view.rerender(<EquipmentPhoto url="/equipment/models/local/photo" name="Banco" />)
  expect(await screen.findByRole('img', { name: 'Imagem de Banco' })).toHaveAttribute('src', 'http://localhost:8000/equipment/models/local/photo')
})
