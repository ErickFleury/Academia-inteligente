import { act, cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { ThemeProvider } from '@mui/material'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, expect, test, vi } from 'vitest'

import { ProgressModerationPage } from './progress-moderation-page'
import { getModerationUpdates, moderateProgressUpdate, type ProgressUpdate } from './progress'
import { theme } from './theme'

vi.mock('./progress', () => ({ getModerationUpdates: vi.fn(), moderateProgressUpdate: vi.fn() }))
afterEach(() => { cleanup(); vi.resetAllMocks(); vi.restoreAllMocks() })

const visible: ProgressUpdate = {
  id: 'post-1', author_name: 'Ana Silva', content: 'Treino concluído', visibility: 'shared',
  moderation_status: 'visible', moderation_reason: null, is_own: false, author_profile_id: null,
  created_at: '2026-09-27T12:00:00Z', updated_at: '2026-09-27T12:00:00Z', edited_at: null,
  like_count: 0, liked_by_viewer: false, comment_count: 0, image_count: 0, images: [],
}
const hidden: ProgressUpdate = { ...visible, id: 'post-2', author_name: 'Bruno Lima', moderation_status: 'hidden', moderation_reason: 'Conteúdo em análise' }

function setup(items = [visible, hidden]) {
  vi.mocked(getModerationUpdates).mockResolvedValue(items)
  return render(<ThemeProvider theme={theme}><MemoryRouter><ProgressModerationPage accessToken="token" onSignOut={vi.fn()} /></MemoryRouter></ThemeProvider>)
}
function enterReason(reason: string) {
  fireEvent.change(screen.getByRole('textbox', { name: 'Motivo da moderação (opcional para excluir)' }), { target: { value: reason } })
}

test('shows saved visibility and the last moderation reason on each post', async () => {
  setup()
  const ana = within(await screen.findByRole('article', { name: 'Publicação de Ana Silva' }))
  const bruno = within(screen.getByRole('article', { name: 'Publicação de Bruno Lima' }))
  expect(ana.getByText('Visível')).toBeInTheDocument()
  expect(ana.getByRole('button', { name: 'Restaurar' })).toBeDisabled()
  expect(bruno.getByText('Oculta')).toBeInTheDocument()
  expect(bruno.getByText('Último motivo de moderação: Conteúdo em análise')).toBeInTheDocument()
  expect(bruno.getByRole('button', { name: 'Ocultar' })).toBeDisabled()
  expect(bruno.getByRole('button', { name: 'Restaurar' })).toBeEnabled()
})

test('hide and restore show success beside the affected post and update its saved status', async () => {
  setup()
  const post = within(await screen.findByRole('article', { name: 'Publicação de Ana Silva' }))
  enterReason('Revisar conteúdo')
  vi.mocked(moderateProgressUpdate).mockResolvedValueOnce({ ...visible, moderation_status: 'hidden', moderation_reason: 'Revisar conteúdo' })
  fireEvent.click(post.getByRole('button', { name: 'Ocultar' }))
  expect(await post.findByText('Publicação ocultada com sucesso.')).toBeInTheDocument()
  expect(post.getByText('Oculta')).toBeInTheDocument()
  expect(post.getByText('Último motivo de moderação: Revisar conteúdo')).toBeInTheDocument()
  expect(moderateProgressUpdate).toHaveBeenLastCalledWith('token', visible.id, 'hide', 'Revisar conteúdo')
  const otherPost = within(screen.getByRole('article', { name: 'Publicação de Bruno Lima' }))
  expect(otherPost.queryByText('Publicação ocultada com sucesso.')).not.toBeInTheDocument()

  enterReason('Conteúdo aprovado')
  vi.mocked(moderateProgressUpdate).mockResolvedValueOnce({ ...visible, moderation_reason: 'Conteúdo aprovado' })
  fireEvent.click(post.getByRole('button', { name: 'Restaurar' }))
  expect(await post.findByText('Publicação restaurada com sucesso.')).toBeInTheDocument()
  expect(post.getByText('Visível')).toBeInTheDocument()
  expect(post.queryByText('Publicação ocultada com sucesso.')).not.toBeInTheDocument()
  expect(post.getByText('Último motivo de moderação: Conteúdo aprovado')).toBeInTheDocument()
  expect(moderateProgressUpdate).toHaveBeenLastCalledWith('token', visible.id, 'restore', 'Conteúdo aprovado')
})

test('reason validation and failed requests keep the saved status and recover after success', async () => {
  setup([visible])
  await screen.findByText('Visível')
  fireEvent.click(screen.getByRole('button', { name: 'Ocultar' }))
  expect(screen.getByRole('alert')).toHaveTextContent('Informe o motivo para ocultar ou restaurar.')
  expect(moderateProgressUpdate).not.toHaveBeenCalled()
  enterReason('Revisar conteúdo')
  vi.mocked(moderateProgressUpdate).mockRejectedValueOnce(new Error('Unavailable'))
  fireEvent.click(screen.getByRole('button', { name: 'Ocultar' }))
  expect(await screen.findByText('Não foi possível aplicar a moderação. Tente novamente.')).toBeInTheDocument()
  expect(screen.getByText('Visível')).toBeInTheDocument()
  expect(screen.getByRole('textbox')).toHaveValue('Revisar conteúdo')
  expect(screen.queryByText('Informe o motivo para ocultar ou restaurar.')).not.toBeInTheDocument()
  vi.mocked(moderateProgressUpdate).mockResolvedValueOnce({ ...visible, moderation_status: 'hidden' })
  fireEvent.click(screen.getByRole('button', { name: 'Ocultar' }))
  expect(await screen.findByText('Publicação ocultada com sucesso.')).toBeInTheDocument()
  expect(screen.queryByText('Não foi possível aplicar a moderação. Tente novamente.')).not.toBeInTheDocument()
})

test('pending moderation prevents duplicate actions and only changes the status after the response', async () => {
  setup([visible])
  await screen.findByText('Visível')
  enterReason('Revisar conteúdo')
  let finish!: (item: ProgressUpdate) => void
  vi.mocked(moderateProgressUpdate).mockReturnValueOnce(new Promise((resolve) => { finish = resolve }))
  fireEvent.click(screen.getByRole('button', { name: 'Ocultar' }))
  const saving = screen.getByRole('button', { name: 'Ocultando...' })
  expect(saving).toBeDisabled()
  fireEvent.click(saving)
  expect(screen.getByRole('button', { name: 'Excluir publicação' })).toBeDisabled()
  expect(screen.getByRole('textbox')).toBeDisabled()
  expect(screen.getByText('Visível')).toBeInTheDocument()
  expect(screen.queryByText('Publicação ocultada com sucesso.')).not.toBeInTheDocument()
  expect(moderateProgressUpdate).toHaveBeenCalledTimes(1)
  await act(async () => { finish({ ...visible, moderation_status: 'hidden' }) })
  expect(screen.getByText('Oculta')).toBeInTheDocument()
  expect(screen.getByRole('button', { name: 'Restaurar' })).toBeEnabled()
})

test('deletion still requires confirmation and leaves success feedback after the card disappears', async () => {
  setup([visible])
  await screen.findByText('Visível')
  const confirm = vi.spyOn(window, 'confirm').mockReturnValueOnce(false).mockReturnValueOnce(true)
  fireEvent.click(screen.getByRole('button', { name: 'Excluir publicação' }))
  expect(moderateProgressUpdate).not.toHaveBeenCalled()
  vi.mocked(moderateProgressUpdate).mockResolvedValueOnce(visible)
  fireEvent.click(screen.getByRole('button', { name: 'Excluir publicação' }))
  expect(await screen.findByText('Publicação excluída com sucesso.')).toBeInTheDocument()
  expect(screen.queryByRole('article')).not.toBeInTheDocument()
  expect(screen.getByText('Nenhuma publicação')).toBeInTheDocument()
  expect(confirm).toHaveBeenCalledTimes(2)
  expect(moderateProgressUpdate).toHaveBeenCalledWith('token', visible.id, 'delete', undefined)
})

test('a loading failure shows an error without claiming that the list is empty', async () => {
  setup()
  vi.mocked(getModerationUpdates).mockRejectedValue(new Error('Unavailable'))
  cleanup()
  render(<ThemeProvider theme={theme}><MemoryRouter><ProgressModerationPage accessToken="token" onSignOut={vi.fn()} /></MemoryRouter></ThemeProvider>)
  await waitFor(() => expect(screen.getByRole('alert')).toHaveTextContent('Não foi possível carregar as publicações.'))
  expect(screen.queryByText('Nenhuma publicação')).not.toBeInTheDocument()
})
