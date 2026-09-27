import { ApiRequestError } from './clients'
import type { PendingPlan, ReviewContent } from './training-review'

const base = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'
export type InstructorClient = { id: string; name: string; onboarding_status: 'draft' | 'completed'; draft_id: string | null; current_id: string | null; responsible_instructor_name: string | null }
export type ClientFilters = { search: string; onboarding: string; training: string; responsibility: string; responsible: string }
export const emptyClientFilters: ClientFilters = { search: '', onboarding: 'all', training: 'all', responsibility: 'all', responsible: '' }
async function request<T>(token: string, path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${base}/instructor/clients${path}`, { ...init, cache: 'no-store', headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' } })
  if (!response.ok) throw new ApiRequestError(response.status === 409 ? 'O cliente já possui um plano ou rascunho. Recarregue o cadastro para continuar.' : response.status === 422 ? 'Verifique os campos e as referências de equipamento.' : response.status === 404 ? 'Cliente não encontrado nesta área.' : response.status === 401 ? 'Sua sessão expirou. Entre novamente.' : response.status === 403 ? 'Você não tem permissão para acessar esta área.' : 'Não foi possível concluir a operação. Tente novamente.', response.status)
  return response.json() as Promise<T>
}
export function searchInstructorClients(token: string, filters: ClientFilters, cursor?: string) {
  const query = new URLSearchParams({ limit: '20' })
  Object.entries(filters).forEach(([key, value]) => { if (value.trim() && (key !== 'responsible' || filters.responsibility === 'specific')) query.set(key, value.trim()) })
  if (cursor) query.set('cursor', cursor)
  return request<{ items: InstructorClient[]; next_cursor: string | null }>(token, `?${query}`)
}
export const getInstructorClient = (token: string, id: string) => request<InstructorClient>(token, `/${id}`)
export const createManualDraft = (token: string, id: string, content: ReviewContent) => request<PendingPlan>(token, `/${id}/draft`, { method: 'POST', body: JSON.stringify(content) })
