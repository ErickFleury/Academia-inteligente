const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

export type EquipmentCatalogItem = {
  id: string; name: string; description: string | null; image_url: string | null; active_quantity: number
}
export type EquipmentAdminModel = EquipmentCatalogItem & {
  active: boolean; created_at: string; updated_at: string
  brand: string | null; manufacturer_model: string | null; category: string | null
  image_source: 'upload' | 'link' | 'none'; image_link: string | null
}
export type EquipmentUnit = {
  id: string; equipment_model_id: string; label: string | null; active: boolean
  operational_state: 'operational' | 'out_of_order'; location: string | null; serial_number: string | null
  created_at: string; updated_at: string
}
export type EquipmentModelInput = {
  name: string; description?: string | null; image_url?: string | null; active?: boolean
  brand?: string | null; manufacturer_model?: string | null; category?: string | null
  initial_quantity?: number; unit_prefix?: string
}
export type EquipmentUnitInput = { label?: string; active?: boolean; location?: string | null; serial_number?: string | null }
export class EquipmentRequestError extends Error {
  constructor(message: string, public status: number, public fields: Record<string, string> = {}) { super(message) }
}
const fieldLabels: Record<string, string> = { name: 'nome', description: 'descrição', image_url: 'link da imagem', brand: 'marca', manufacturer_model: 'modelo do fabricante', category: 'categoria', initial_quantity: 'quantidade', quantity: 'quantidade', unit_prefix: 'prefixo', prefix: 'prefixo', label: 'identificador', location: 'localização', serial_number: 'número de série' }
async function failure(response: Response): Promise<never> {
  const body = await response.json().catch(() => null)
  const fields: Record<string, string> = {}
  if (Array.isArray(body?.detail)) for (const issue of body.detail) {
    const field = issue.loc?.at(-1)
    if (fieldLabels[field]) fields[field] = `Verifique o campo ${fieldLabels[field]}.`
  }
  const known: Record<string, string> = {
    'Equipment name is required': 'Informe o nome do equipamento.',
    'Invalid image URL': 'Use um link http/https ou um caminho de imagem válido.',
    'Image size is invalid': 'Escolha uma imagem de até 5 MB.',
    'Invalid image': 'Não foi possível ler a imagem. Escolha outro arquivo JPEG, PNG ou WebP.',
    'Unsupported image': 'Escolha uma imagem estática JPEG, PNG ou WebP.',
    'Image dimensions are too large': 'A imagem tem dimensões muito grandes. Escolha uma versão menor.',
  }
  const message = response.status === 401 ? 'Sua sessão expirou. Entre novamente.'
    : response.status === 403 ? 'Você não tem permissão para gerenciar equipamentos.'
      : response.status === 404 ? 'Equipamento não encontrado. Recarregue a lista.'
        : response.status === 413 ? 'Escolha uma imagem de até 5 MB.'
          : known[body?.detail] || (response.status === 422 ? 'Verifique os campos informados.' : 'Não foi possível concluir esta ação. Tente novamente.')
  throw new EquipmentRequestError(message, response.status, fields)
}
async function request<T>(path: string, init?: RequestInit, accessToken?: string): Promise<T> {
  let response: Response
  try {
    response = await fetch(`${apiBaseUrl}${path}`, { ...init, cache: 'no-store', headers: {
      ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
      'Content-Type': 'application/json', ...init?.headers,
    } })
  } catch { throw new EquipmentRequestError('Não foi possível conectar. Verifique sua conexão e tente novamente.', 0) }
  if (!response.ok) return failure(response)
  return response.status === 204 ? undefined as T : response.json() as Promise<T>
}
export const equipmentImageUrl = (url: string) => url.startsWith('/equipment/') ? `${apiBaseUrl}${url}` : url
export const getEquipmentCatalog = () => request<EquipmentCatalogItem[]>('/equipment')
export const getEquipmentModels = (token: string) => request<EquipmentAdminModel[]>('/equipment/admin/models', undefined, token)
export const createEquipmentModel = (token: string, input: EquipmentModelInput) => request<EquipmentAdminModel>('/equipment/admin/models', { method: 'POST', body: JSON.stringify(input) }, token)
export const updateEquipmentModel = (token: string, id: string, input: Partial<EquipmentModelInput>) => request<EquipmentAdminModel>(`/equipment/admin/models/${id}`, { method: 'PATCH', body: JSON.stringify(input) }, token)
export const getEquipmentUnits = (token: string, modelId: string) => request<EquipmentUnit[]>(`/equipment/admin/models/${modelId}/units`, undefined, token)
export const createEquipmentUnits = (token: string, modelId: string, quantity: number, prefix: string) => request<EquipmentUnit[]>(`/equipment/admin/models/${modelId}/units/batch`, { method: 'POST', body: JSON.stringify({ quantity, prefix }) }, token)
export const updateEquipmentUnit = (token: string, unitId: string, input: EquipmentUnitInput) => request<EquipmentUnit>(`/equipment/admin/units/${unitId}`, { method: 'PATCH', body: JSON.stringify(input) }, token)
export const uploadEquipmentImage = (token: string, id: string, file: File) => request<EquipmentAdminModel>(`/equipment/admin/models/${id}/image`, { method: 'PUT', headers: { 'Content-Type': 'application/octet-stream' }, body: file }, token)
