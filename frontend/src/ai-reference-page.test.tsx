import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { AiReferencePage } from './ai-reference-page'
import * as api from './ai-references'

vi.mock('./ai-references', () => ({ listReferences: vi.fn(), previewReference: vi.fn(), referenceAction: vi.fn(), uploadReference: vi.fn(), deleteReference: vi.fn() }))
const item: api.ReferenceVersion = { id: 'version', source_id: 'source', title: 'Manual de treino', number: 1, status: 'ready', active: false, progress: 100, error_code: null, revision: 1 }
afterEach(() => { cleanup(); vi.resetAllMocks() })
function mount() { render(<MemoryRouter><AiReferencePage accessToken="test-token" onSignOut={() => {}} /></MemoryRouter>) }

describe('referências do assistente', () => {
  it('requires text preview before offering activation', async () => {
    vi.mocked(api.listReferences).mockResolvedValue([item])
    vi.mocked(api.previewReference).mockResolvedValue([{ position: 1, location: 'page:1', content: 'Texto do manual.' }])
    vi.mocked(api.referenceAction).mockResolvedValue({ ...item, active: true, status: 'active' })
    mount()
    await screen.findByText('Manual de treino · versão 1')
    expect(screen.queryByRole('button', { name: 'Ativar esta versão' })).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Conferir texto' }))
    await screen.findByText('Texto do manual.')
    fireEvent.click(screen.getByRole('button', { name: 'Ativar esta versão' }))
    await waitFor(() => expect(api.referenceAction).toHaveBeenCalledWith('test-token', item, 'activate'))
  })
  it('requires confirmation before withdrawing an active reference', async () => {
    vi.mocked(api.listReferences).mockResolvedValue([{ ...item, active: true, status: 'active' }])
    mount()
    fireEvent.click(await screen.findByRole('button', { name: 'Retirar referência' }))
    expect(api.referenceAction).not.toHaveBeenCalled()
    expect(screen.getByText('Retirar referência?')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Cancelar' }))
    expect(api.referenceAction).not.toHaveBeenCalled()
  })
  it('shows a controlled permission failure', async () => {
    vi.mocked(api.listReferences).mockRejectedValue(new Error('Você não tem permissão para gerenciar referências.'))
    mount()
    expect(await screen.findByRole('alert')).toHaveTextContent('Você não tem permissão')
  })
  it('confirms deleting every version and clears the list after deletion', async () => {
    vi.mocked(api.listReferences).mockResolvedValue([item, { ...item, id: 'old-version', number: 2 }])
    vi.mocked(api.deleteReference).mockImplementation(async () => {
      vi.mocked(api.listReferences).mockResolvedValue([])
    })
    mount()
    fireEvent.click((await screen.findAllByRole('button', { name: 'Excluir referência' }))[0])
    const dialog = screen.getByRole('dialog', { name: 'Excluir referência permanentemente?' })
    expect(dialog).toHaveTextContent('todas as versões')
    expect(dialog).toHaveTextContent('Manual de treino')
    expect(api.deleteReference).not.toHaveBeenCalled()
    fireEvent.click(within(dialog).getByRole('button', { name: 'Cancelar' }))
    expect(api.deleteReference).not.toHaveBeenCalled()
    fireEvent.click((await screen.findAllByRole('button', { name: 'Excluir referência' }))[0])
    fireEvent.click(screen.getByRole('button', { name: 'Excluir permanentemente' }))
    await screen.findByText('Nenhuma referência cadastrada')
    expect(api.deleteReference).toHaveBeenCalledExactlyOnceWith('test-token', item)
    expect(screen.queryByText('Manual de treino · versão 2')).not.toBeInTheDocument()
  })
  it('shows deletion failure inside the dialog and preserves the reference', async () => {
    vi.mocked(api.listReferences).mockResolvedValue([item])
    vi.mocked(api.deleteReference).mockRejectedValue(new Error('Esta referência mudou. Atualize a lista e tente novamente.'))
    mount()
    fireEvent.click(await screen.findByRole('button', { name: 'Excluir referência' }))
    fireEvent.click(screen.getByRole('button', { name: 'Excluir permanentemente' }))
    const dialog = screen.getByRole('dialog', { name: 'Excluir referência permanentemente?' })
    expect(await within(dialog).findByRole('alert')).toHaveTextContent('Esta referência mudou')
    expect(screen.getByText('Manual de treino · versão 1')).toBeInTheDocument()
  })
})
