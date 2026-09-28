import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, expect, test, vi } from 'vitest'
import { MemoryRouter, Route, Routes } from 'react-router-dom'

import { ProfileConnectionsDialog } from './profile-connections-dialog'

afterEach(() => { cleanup(); vi.unstubAllGlobals() })
const member = (id: number) => ({ id: `profile-${id}`, name: `Pessoa ${id}`, nickname: null, has_image: false })

test.each(['followers', 'following'] as const)('loads %s and links to profiles', async (direction) => {
  const fetch = vi.fn(async () => ({ ok: true, json: async () => [member(1)] }))
  vi.stubGlobal('fetch', fetch)
  const close = vi.fn()
  render(<ProfileConnectionsDialog accessToken="token" profileId="owner" direction={direction} onClose={close} />)
  const link = await screen.findByRole('link', { name: /Pessoa 1/ })
  expect(link).toHaveAttribute('href', '/perfis/profile-1')
  expect(fetch).toHaveBeenCalledWith(`http://localhost:8000/social-profiles/profiles/owner/graph/${direction}?offset=0&limit=20`, expect.objectContaining({ headers: { Authorization: 'Bearer token' } }))
  fireEvent.click(screen.getByRole('button', { name: 'Fechar' }))
  expect(close).toHaveBeenCalledOnce()
})

test('loads another page without losing previous profiles or duplicating rows', async () => {
  const fetch = vi.fn()
    .mockResolvedValueOnce({ ok: true, json: async () => Array.from({ length: 20 }, (_, id) => member(id)) })
    .mockResolvedValueOnce({ ok: true, json: async () => [member(19), member(20)] })
  vi.stubGlobal('fetch', fetch)
  render(<ProfileConnectionsDialog accessToken="token" profileId="owner" direction="followers" onClose={vi.fn()} />)
  fireEvent.click(await screen.findByRole('button', { name: 'Carregar mais' }))
  await screen.findByRole('link', { name: /Pessoa 20/ })
  expect(screen.getAllByRole('link')).toHaveLength(21)
  expect(fetch.mock.calls[1][0]).toContain('offset=20')
  expect(screen.queryByRole('button', { name: 'Carregar mais' })).not.toBeInTheDocument()
})

test('clears inaccessible rows on error and retries from the first page', async () => {
  const fetch = vi.fn()
    .mockResolvedValueOnce({ ok: true, json: async () => Array.from({ length: 20 }, (_, id) => member(id)) })
    .mockResolvedValueOnce({ ok: false, status: 403 })
    .mockResolvedValueOnce({ ok: true, json: async () => [] })
  vi.stubGlobal('fetch', fetch)
  render(<ProfileConnectionsDialog accessToken="token" profileId="owner" direction="following" onClose={vi.fn()} />)
  fireEvent.click(await screen.findByRole('button', { name: 'Carregar mais' }))
  await screen.findByText(/Não foi possível carregar esta lista/)
  expect(screen.queryByRole('link')).not.toBeInTheDocument()
  fireEvent.click(screen.getByRole('button', { name: 'Tentar novamente' }))
  expect(await screen.findByText('Nenhum perfil seguido disponível')).toBeInTheDocument()
  expect(fetch.mock.calls[2][0]).toContain('offset=0')
})

test('selecting a person closes the dialog and navigates to their profile', async () => {
  vi.stubGlobal('fetch', vi.fn(async () => ({ ok: true, json: async () => [member(1)] })))
  const close = vi.fn()
  render(<MemoryRouter><Routes>
    <Route path="/" element={<ProfileConnectionsDialog accessToken="token" profileId="owner" direction="followers" onClose={close} />} />
    <Route path="/perfis/profile-1" element={<h1>Perfil selecionado</h1>} />
  </Routes></MemoryRouter>)
  fireEvent.click(await screen.findByRole('link', { name: /Pessoa 1/ }))
  expect(await screen.findByRole('heading', { name: 'Perfil selecionado' })).toBeInTheDocument()
  expect(close).toHaveBeenCalledOnce()
})
