const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'

export type EquipmentCatalogItem = {
  id: string
  name: string
  description: string | null
  image_url: string | null
  active_quantity: number
}

export type EquipmentAdminModel = EquipmentCatalogItem & {
  active: boolean
  created_at: string
  updated_at: string
}

export type EquipmentUnit = {
  id: string
  equipment_model_id: string
  label: string | null
  active: boolean
  created_at: string
  updated_at: string
}

export type EquipmentModelInput = {
  name: string
  description?: string | null
  image_url?: string | null
  active?: boolean
}

async function request<T>(path: string, init?: RequestInit, accessToken?: string): Promise<T> {
  const response = await fetch(`${apiBaseUrl}${path}`, {
    ...init,
    headers: {
      ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
      'Content-Type': 'application/json',
      ...init?.headers,
    },
  })
  if (!response.ok) {
    const body = await response.json().catch(() => null) as { detail?: string } | null
    throw new Error(body?.detail || 'Não foi possível concluir esta ação. Tente novamente.')
  }
  return response.json() as Promise<T>
}

export const getEquipmentCatalog = () => request<EquipmentCatalogItem[]>('/equipment')
export const getEquipmentModels = (token: string) => request<EquipmentAdminModel[]>('/equipment/admin/models', undefined, token)
export const createEquipmentModel = (token: string, input: EquipmentModelInput) => request<EquipmentAdminModel>('/equipment/admin/models', { method: 'POST', body: JSON.stringify(input) }, token)
export const updateEquipmentModel = (token: string, id: string, input: Partial<EquipmentModelInput>) => request<EquipmentAdminModel>(`/equipment/admin/models/${id}`, { method: 'PATCH', body: JSON.stringify(input) }, token)
export const getEquipmentUnits = (token: string, modelId: string) => request<EquipmentUnit[]>(`/equipment/admin/models/${modelId}/units`, undefined, token)
export const createEquipmentUnit = (token: string, modelId: string, label: string) => request<EquipmentUnit>(`/equipment/admin/models/${modelId}/units`, { method: 'POST', body: JSON.stringify({ label, active: true }) }, token)
export const updateEquipmentUnit = (token: string, unitId: string, input: { label?: string | null; active?: boolean }) => request<EquipmentUnit>(`/equipment/admin/units/${unitId}`, { method: 'PATCH', body: JSON.stringify(input) }, token)
