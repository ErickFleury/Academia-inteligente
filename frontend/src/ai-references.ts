const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

export type ReferenceVersion = {
  id: string; source_id: string; title: string; number: number; status: string
  active: boolean; progress: number; error_code: string | null; revision: number
}
export type ReferencePreview = { position: number; location: string; content: string }
const messages: Record<string, string> = {
  reference_conflict: 'Esta referência mudou. Atualize a lista e tente novamente.',
  reference_not_found: 'Esta referência não está mais disponível. Atualize a lista.',
  reference_not_ready: 'A referência precisa concluir o processamento antes da ativação.',
  reference_capacity: 'O limite de referências ativas foi atingido. Retire uma referência antes de continuar.',
  document_size: 'Escolha um documento de até 150 MB.',
  import_queue_full: 'Há muitos documentos aguardando processamento. Tente novamente em alguns minutos.',
}
async function request<T>(token: string, path = '', init?: RequestInit): Promise<T> {
  let response: Response
  try {
    response = await fetch(`${apiBaseUrl}/ai/references${path}`, {
      ...init, cache: 'no-store', headers: { Authorization: `Bearer ${token}`, ...init?.headers },
    })
  } catch { throw new Error('Não foi possível conectar ao servidor. Tente novamente.') }
  if (!response.ok) {
    const data = await response.json().catch(() => ({}))
    throw new Error(response.status === 403 ? 'Você não tem permissão para gerenciar referências.'
      : response.status === 401 ? 'Sua sessão expirou. Entre novamente.'
        : messages[data.detail] || 'Não foi possível concluir esta ação. Tente novamente.')
  }
  return response.status === 204 ? undefined as T : response.json()
}
export const listReferences = (token: string) => request<ReferenceVersion[]>(token)
export const previewReference = (token: string, id: string, offset = 0) =>
  request<ReferencePreview[]>(token, `/${id}/preview?offset=${offset}`)
export const referenceAction = (token: string, item: ReferenceVersion, action: 'activate' | 'withdraw' | 'retry') =>
  request<ReferenceVersion>(token, `/${item.id}/actions`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ action, revision: item.revision }),
  })
export const deleteReference = (token: string, item: Pick<ReferenceVersion, 'source_id' | 'revision'>) =>
  request<void>(token, `/sources/${item.source_id}`, {
    method: 'DELETE', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ revision: item.revision }),
  })
export function uploadReference(token: string, title: string, file: File, sourceId?: string) {
  const extension = file.name.split('.').at(-1)?.toLowerCase()
  const types: Record<string, string> = { pdf: 'application/pdf', md: 'text/markdown', txt: 'text/plain' }
  const mediaType = types[extension || '']
  if (!mediaType || file.size === 0 || file.size > 150 * 1024 * 1024) throw new Error('Escolha um arquivo PDF, Markdown ou TXT de até 150 MB.')
  const query = new URLSearchParams({ title, media_type: mediaType })
  if (sourceId) query.set('source_id', sourceId)
  return request<ReferenceVersion>(token, `?${query}`, {
    method: 'POST', headers: { 'Content-Type': 'application/octet-stream' }, body: file,
  })
}
