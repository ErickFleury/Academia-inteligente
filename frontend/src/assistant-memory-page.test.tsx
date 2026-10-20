import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { AssistantMemoryPage } from './assistant-memory-page'
import * as api from './assistant-memory'

vi.mock('./assistant-memory', () => ({ getMemory: vi.fn(), correctMemory: vi.fn(), forgetMemory: vi.fn() }))
const state: api.MemorySnapshot = { revision: 2, facts: [{ id: 'fact', category: 'health_report', text: 'Tenho dor no joelho.', attribution: 'client_report', reported_at: '2026-10-19T12:00:00Z', updated_at: '2026-10-19T12:00:00Z' }] }
afterEach(() => { cleanup(); vi.resetAllMocks() })
function mount() { render(<MemoryRouter><AssistantMemoryPage accessToken="token" onSignOut={() => {}} /></MemoryRouter>) }
describe('memória do assistente', () => {
  it('saves a correction with the revision shown when editing began', async () => {
    vi.mocked(api.getMemory).mockResolvedValue(state)
    vi.mocked(api.correctMemory).mockResolvedValue({ ...state, revision: 3 })
    mount()
    fireEvent.click(await screen.findByRole('button', { name: 'Corrigir: Tenho dor no joelho.' }))
    fireEvent.change(screen.getByLabelText('Seu relato ou preferência'), { target: { value: 'Tenho dor no joelho esquerdo.' } })
    fireEvent.click(screen.getByRole('button', { name: 'Salvar correção' }))
    await waitFor(() => expect(api.correctMemory).toHaveBeenCalledWith('token', 'fact', 2, 'Tenho dor no joelho esquerdo.'))
    expect(await screen.findByText('Memória atualizada.')).toBeInTheDocument()
  })
  it('requires confirmation to forget and then removes the fact', async () => {
    vi.mocked(api.getMemory).mockResolvedValue(state)
    vi.mocked(api.forgetMemory).mockResolvedValue({ revision: 3, facts: [] })
    mount()
    fireEvent.click(await screen.findByRole('button', { name: 'Esquecer: Tenho dor no joelho.' }))
    expect(api.forgetMemory).not.toHaveBeenCalled()
    fireEvent.click(screen.getByRole('button', { name: 'Confirmar esquecimento' }))
    expect(await screen.findByText('Nenhuma memória guardada')).toBeInTheDocument()
    expect(api.forgetMemory).toHaveBeenCalledWith('token', 'fact', 2)
  })
  it('preserves the displayed fact on a conflict and offers refresh', async () => {
    vi.mocked(api.getMemory).mockResolvedValue(state)
    vi.mocked(api.forgetMemory).mockRejectedValue(new Error('Sua memória mudou. Atualize a lista.'))
    mount()
    fireEvent.click(await screen.findByRole('button', { name: 'Esquecer: Tenho dor no joelho.' }))
    fireEvent.click(screen.getByRole('button', { name: 'Confirmar esquecimento' }))
    expect(await screen.findByText('Sua memória mudou. Atualize a lista.')).toBeInTheDocument()
    expect(screen.getByText('Tenho dor no joelho.')).toBeInTheDocument()
  })
})
