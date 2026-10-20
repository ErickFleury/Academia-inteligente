const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'
export type MemoryFact = {
  id: string; category: 'health_report' | 'preference' | 'training_goal'; text: string
  attribution: 'client_report' | 'client_edit'; reported_at: string; updated_at: string
}
export type MemorySnapshot = { revision: number; facts: MemoryFact[] }
async function request(token: string, path = '', init?: RequestInit): Promise<MemorySnapshot> {
  let response: Response
  try {
    response = await fetch(`${apiBaseUrl}/ai/memory${path}`, {
      ...init, cache: 'no-store', headers: { Authorization: `Bearer ${token}`, ...init?.headers },
    })
  } catch { throw new Error('Não foi possível conectar ao servidor. Tente novamente.') }
  if (!response.ok) {
    const data = await response.json().catch(() => ({}))
    throw new Error(data.detail === 'memory_capacity' ? 'A memória está cheia. Revise ou remova informações antes de continuar.'
      : response.status === 409 ? 'Sua memória mudou. Atualize a lista e confira as informações antes de tentar novamente.'
        : response.status === 403 ? 'Somente você pode acessar sua memória do assistente.'
          : response.status === 401 ? 'Sua sessão expirou. Entre novamente.'
            : 'Não foi possível concluir esta ação. Tente novamente.')
  }
  return response.json()
}
export const getMemory = (token: string) => request(token)
export const correctMemory = (token: string, id: string, revision: number, text: string) =>
  request(token, `/${id}`, { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ revision, text }) })
export const forgetMemory = (token: string, id: string, revision: number) =>
  request(token, `/${id}?revision=${revision}`, { method: 'DELETE' })
