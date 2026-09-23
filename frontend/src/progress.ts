const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'

export type ProgressUpdate = { id: string; author_name: string; content: string; visibility: 'private' | 'shared'; moderation_status: 'visible' | 'hidden'; moderation_reason: string | null; is_own: boolean; created_at: string; updated_at: string }

async function request<T>(path: string, token: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${apiBaseUrl}${path}`, { ...init, headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json', ...init?.headers } })
  if (!response.ok) throw new Error('Não foi possível concluir esta ação. Tente novamente.')
  return response.status === 204 ? undefined as T : response.json() as Promise<T>
}
export const getProgressFeed = (token: string) => request<ProgressUpdate[]>('/progress', token)
export const createProgressUpdate = (token: string, content: string, visibility: 'private' | 'shared') => request<ProgressUpdate>('/progress', token, { method: 'POST', body: JSON.stringify({ content, visibility }) })
export const deleteProgressUpdate = (token: string, id: string) => request<void>(`/progress/${id}`, token, { method: 'DELETE' })
export const getModerationUpdates = (token: string) => request<ProgressUpdate[]>('/progress/moderation/updates', token)
export const moderateProgressUpdate = (token: string, id: string, action: 'hide' | 'restore' | 'delete', reason?: string) => request<ProgressUpdate>(`/progress/moderation/updates/${id}`, token, { method: 'POST', body: JSON.stringify({ action, reason }) })
