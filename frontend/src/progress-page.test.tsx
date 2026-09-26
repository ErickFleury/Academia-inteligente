import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, expect, test, vi } from 'vitest'
import { ProgressPage } from './progress-page'

afterEach(() => { cleanup(); vi.unstubAllGlobals() })

test('creates a private progress update with Portuguese privacy guidance', async () => {
  const fetchMock = vi.fn().mockResolvedValueOnce({ ok: true, json: async () => ({ items: [], next_cursor: null, end_reached: true }) }).mockResolvedValueOnce({ ok: true, json: async () => ({ id: 'update-1', author_name: 'Ada', content: 'Treino concluído', visibility: 'private', moderation_status: 'visible', moderation_reason: null, is_own: true, author_profile_id: null, edited_at: null, like_count: 0, comment_count: 0, image_count: 0, created_at: '2026-09-23T12:00:00Z', updated_at: '2026-09-23T12:00:00Z' }) })
  vi.stubGlobal('fetch', fetchMock)
  render(<ProgressPage accessToken="token" onSignOut={vi.fn()} />)
  fireEvent.change(await screen.findByLabelText('Sua atualização'), { target: { value: 'Treino concluído' } })
  fireEvent.click(screen.getByRole('button', { name: 'Publicar atualização' }))
  expect(await screen.findByText('Treino concluído')).toBeInTheDocument()
  expect(screen.getByText('Visível somente para você')).toBeInTheDocument()
  expect(fetchMock.mock.calls[1][1]).toMatchObject({ method: 'POST', headers: { Authorization: 'Bearer token' } })
})
