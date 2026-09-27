import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, expect, test, vi } from 'vitest'

import { SocialProfilePage } from './social-profile-page'

vi.mock('./occupancy', () => ({ getOccupancy: async () => ({ occupancy: 0 }) }))
afterEach(() => { cleanup(); vi.unstubAllGlobals() })

test.each([true, false])('password recovery is available only in the profile owner settings: %s', async (owner) => {
  const fetch = vi.fn(async (url: string) => ({ ok: true, json: async () =>
    url.includes('/posts') ? [] : url.includes('/profile-presence/') ? { sharing_enabled: false, currently_present: false } : {
      id: 'profile-1', name: 'Ada', nickname: null, biography: null, has_image: false,
      is_owner: owner, visible_to_clients: true, follower_count: 0, following_count: 0, pending_follow_request_count: 0,
    },
  }))
  vi.stubGlobal('fetch', fetch)
  render(<SocialProfilePage accessToken="test-token" onSignOut={vi.fn()} profileId={owner ? undefined : 'profile-1'} />)
  await screen.findByRole('heading', { name: 'Ada', level: 2 })
  if (owner) {
    fireEvent.click(screen.getByRole('button', { name: 'Configurações do perfil' }))
    fireEvent.click(screen.getByRole('button', { name: 'Redefinir senha' }))
    await screen.findByText(/E-mail de redefinição enviado/)
    expect(fetch).toHaveBeenCalledWith('http://localhost:8000/identity/me/password-reset', expect.objectContaining({ method: 'POST' }))
  } else {
    expect(screen.queryByRole('button', { name: 'Configurações do perfil' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Redefinir senha' })).not.toBeInTheDocument()
  }
})

test.each([true, false])('presence toggle applies the confirmed server state immediately: inside=%s', async (inside) => {
  const fetch = vi.fn(async (url: string, init?: RequestInit) => ({ ok: true, json: async () =>
    url.includes('/posts') ? [] : url.includes('/profile-presence/') ? {
      sharing_enabled: init?.method === 'PATCH' && JSON.parse(init.body as string).enabled,
      currently_present: inside && init?.method === 'PATCH' && JSON.parse(init.body as string).enabled,
    } : { id: 'profile-1', name: 'Ada', has_image: false, is_owner: true, visible_to_clients: true, currently_present: false },
  }))
  vi.stubGlobal('fetch', fetch)
  render(<SocialProfilePage accessToken="test-token" onSignOut={vi.fn()} />)
  fireEvent.click(await screen.findByRole('button', { name: 'Configurações do perfil' }))
  const toggle = await screen.findByRole('switch', { name: 'Mostrar no meu perfil quando eu estiver na academia' })
  fireEvent.click(toggle)
  await waitFor(() => expect(toggle).toBeChecked())
  if (inside) expect(screen.getByText('Na academia')).toBeInTheDocument()
  else expect(screen.queryByText('Na academia')).not.toBeInTheDocument()
  fireEvent.click(toggle)
  await waitFor(() => expect(toggle).not.toBeChecked())
  expect(screen.queryByText('Na academia')).not.toBeInTheDocument()
})

test('failed presence updates keep the saved preference and show an error in settings', async () => {
  vi.stubGlobal('fetch', vi.fn(async (url: string, init?: RequestInit) => ({ ok: init?.method !== 'PATCH', json: async () =>
    url.includes('/posts') ? [] : url.includes('/profile-presence/') ? { sharing_enabled: false, currently_present: false }
      : { id: 'profile-1', name: 'Ada', has_image: false, is_owner: true, visible_to_clients: true, currently_present: false },
  })))
  render(<SocialProfilePage accessToken="test-token" onSignOut={vi.fn()} />)
  fireEvent.click(await screen.findByRole('button', { name: 'Configurações do perfil' }))
  const toggle = await screen.findByRole('switch', { name: 'Mostrar no meu perfil quando eu estiver na academia' })
  fireEvent.click(toggle)
  expect(await screen.findByText('Não foi possível salvar a preferência de presença. Tente novamente.')).toBeInTheDocument()
  expect(toggle).not.toBeChecked()
  expect(toggle).not.toBeDisabled()
  expect(screen.queryByText('Na academia')).not.toBeInTheDocument()
})
