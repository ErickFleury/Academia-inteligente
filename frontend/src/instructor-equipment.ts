import { ApiRequestError } from './clients'
const base = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'
export type OperationalUnit = { id: string; label: string | null; active: boolean; operational_state: 'operational' | 'out_of_order'; revision: number }
export type InstructorEquipmentModel = { id: string; name: string; active_quantity: number }
export type EquipmentPage<T> = { items: T[]; next_cursor: string | null }
async function request<T>(token: string, path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${base}/instructor/equipment${path}`, { ...init, cache: 'no-store', headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' } })
  if (!response.ok) throw new ApiRequestError(response.status === 409 ? 'A unidade mudou ou foi desativada. Recarregue antes de continuar.' : response.status === 404 ? 'Equipamento não encontrado nesta área.' : response.status === 401 ? 'Sua sessão expirou. Entre novamente.' : response.status === 403 ? 'Você não tem permissão para alterar o estado dos equipamentos.' : 'Não foi possível carregar ou atualizar os equipamentos. Tente novamente.', response.status)
  return response.json() as Promise<T>
}
const query = (cursor?: string) => `?limit=20${cursor ? `&cursor=${encodeURIComponent(cursor)}` : ''}`
export const getInstructorEquipment = (token: string, cursor?: string) => request<EquipmentPage<InstructorEquipmentModel>>(token, query(cursor))
export const getOperationalUnits = (token: string, id: string, cursor?: string) => request<EquipmentPage<OperationalUnit>>(token, `/${id}/units${query(cursor)}`)
export const setOperationalState = (token: string, unit: OperationalUnit) => request<OperationalUnit>(token, `/units/${unit.id}/operational-state`, { method: 'PATCH', body: JSON.stringify({ operational_state: unit.operational_state === 'operational' ? 'out_of_order' : 'operational', expected_revision: unit.revision }) })

export type UsableEquipmentModel = { id: string; name: string }
export const getUsableEquipment = (token: string, cursor?: string) => request<{ items: UsableEquipmentModel[]; next_cursor: string | null }>(token, `/usable-models?limit=20${cursor ? `&cursor=${encodeURIComponent(cursor)}` : ''}`)
