import { ApiRequestError } from './clients'
import type { PendingPlan, ReviewContent } from './training-review'

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'
export type ApprovedPlan = { id: string; name: string; client_name: string; status: 'current' | 'approved' | 'superseded'; revision: number; approved_at: string; responsible_instructor_name: string | null }
export type ApprovedDetail = ApprovedPlan & ReviewContent
export type CollectionPage = { items: ApprovedPlan[]; next_cursor: string | null }
export type DraftConflict = { id: string; name: string; revision: number }
export class ExistingDraftError extends Error {
  constructor(public draft: DraftConflict) { super('Já existe um rascunho para este cliente.') }
}
export type PlanFilters = { search: string; responsible: string; start: string; end: string }
export const emptyFilters: PlanFilters = { search: '', responsible: '', start: '', end: '' }

async function request<T>(token: string, path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${apiBaseUrl}/training/collections${path}`, { ...init, cache: 'no-store', headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' } })
  if (!response.ok) {
    const body = await response.json().catch(() => null)
    if (response.status === 409 && body?.detail?.code === 'existing_draft') throw new ExistingDraftError(body.detail.draft)
    throw new ApiRequestError(response.status === 409 ? 'O plano ou rascunho mudou. Recarregue e revise antes de continuar.' : response.status === 422 ? 'Verifique os filtros e o intervalo de datas.' : response.status === 401 ? 'Sua sessão expirou. Entre novamente.' : response.status === 403 ? 'Você não tem permissão para acessar os planos.' : 'Não foi possível carregar ou editar o plano. Tente novamente.', response.status)
  }
  return response.json() as Promise<T>
}
export function getPlanCollection(token: string, mine: boolean, filters: PlanFilters, cursor?: string) {
  const params = new URLSearchParams({ mine: String(mine), limit: '20' })
  Object.entries(filters).forEach(([key, value]) => { if (value.trim()) params.set(key, value.trim()) })
  if (cursor) params.set('cursor', cursor)
  return request<CollectionPage>(token, `?${params}`)
}
export const getApprovedPlan = (token: string, id: string) => request<ApprovedDetail>(token, `/${id}`)
export const getPlanHistory = (token: string, id: string, cursor?: string) => request<CollectionPage>(token, `/${id}/history?limit=20${cursor ? `&cursor=${encodeURIComponent(cursor)}` : ''}`)
export const getResponsibleOptions = (token: string, cursor?: string) => request<{ items: { reference: string; name: string }[]; next_cursor: string | null }>(token, `/responsible${cursor ? `?cursor=${encodeURIComponent(cursor)}` : ''}`)
export const cloneCurrentPlan = (token: string, plan: ApprovedPlan, discard?: DraftConflict) => request<PendingPlan>(token, `/${plan.id}/draft`, { method: 'POST', body: JSON.stringify({ expected_revision: plan.revision, ...(discard ? { discard_id: discard.id, discard_revision: discard.revision } : {}) }) })
