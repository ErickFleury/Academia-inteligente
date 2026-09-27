import { cleanup, fireEvent, render, screen } from '@testing-library/react'
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
