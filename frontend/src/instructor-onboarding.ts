import type { OnboardingDraft, OnboardingDraftUpdate } from './onboarding-draft'
const base = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'
async function request(token: string, id: string, method: string, payload?: OnboardingDraftUpdate): Promise<OnboardingDraft> {
  const response = await fetch(`${base}/instructor/clients/${encodeURIComponent(id)}/onboarding${method === 'POST' ? '/completion' : ''}`, { method, cache: 'no-store', headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' }, ...(payload ? { body: JSON.stringify(payload) } : {}) })
  if (!response.ok) throw new Error(response.status === 422 ? 'Revise os campos obrigatórios e as informações de saúde antes de salvar ou concluir.' : response.status === 409 ? 'Este onboarding já foi concluído. Reabra o cadastro para editar os dados.' : response.status === 401 ? 'Sua sessão expirou. Entre novamente.' : [403, 404].includes(response.status) ? 'Este onboarding não está disponível para seu acesso.' : 'Não foi possível concluir a operação de onboarding. Tente novamente.')
  return response.json() as Promise<OnboardingDraft>
}
export const readInstructorOnboarding = (token: string, id: string) => request(token, id, 'GET')
export const saveInstructorOnboarding = (token: string, id: string, payload: OnboardingDraftUpdate) => request(token, id, 'PATCH', payload)
export const completeInstructorOnboarding = (token: string, id: string) => request(token, id, 'POST')
