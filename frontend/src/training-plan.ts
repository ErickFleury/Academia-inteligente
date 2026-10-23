import { clarificationMessage } from './assistant-clarification'
import type { SupportingReference } from './components/supporting-references'
const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'

export type CurrentTrainingItem = {
  exercise_name: string
  sets: number
  repetitions: string
  load_guidance: string
  rest_seconds: number
  position: number
  equipment_requirement?: string | null
  equipment_model_id?: string | null
}

export type CurrentTrainingPlan = {
  reference_citations?: SupportingReference[]
  plan_id: string
  version_number: number
  status: 'current'
  name: string
  objective: string
  responsible_instructor_name: string | null
  approved_at: string | null
  items: CurrentTrainingItem[]
}

export type TrainingPlanDraft = Omit<CurrentTrainingPlan, 'status'> & {
  status: 'proposal'
  origin: 'ai' | 'instructor'
}

export async function createInitialTrainingProposal(accessToken: string): Promise<TrainingPlanDraft> {
  const response = await fetch(`${apiBaseUrl}/training/initial-proposal`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${accessToken}` },
  })
  if (response.status === 401) throw new Error('Sua sessão expirou. Entre novamente para continuar.')
  if (response.status === 403) throw new Error('Você não tem permissão para gerar seu rascunho de treino.')
  if (response.status === 422) {
    const data = await response.json().catch(() => ({}))
    if (data.detail === 'assistant_clarification_required') throw new Error(clarificationMessage(data.clarification, 'Confirme seus relatos relevantes no assistente ou consulte seu instrutor antes de gerar a proposta.'))
    throw new Error('Conclua seu onboarding e confira as informações antes de gerar seu rascunho de treino.')
  }
  if (response.status === 503) throw new Error('A geração por IA está indisponível no momento. Tente novamente.')
  if (!response.ok) throw new Error('Não foi possível gerar seu rascunho de treino. Tente novamente.')
  return response.json() as Promise<TrainingPlanDraft>
}

export async function getCurrentTrainingPlan(accessToken: string): Promise<CurrentTrainingPlan | null> {
  const response = await fetch(`${apiBaseUrl}/training/current`, {
    headers: { Authorization: `Bearer ${accessToken}` },
  })
  if (response.status === 401) throw new Error('Sua sessão expirou. Entre novamente para continuar.')
  if (response.status === 403) throw new Error('Você não tem permissão para acessar seu treino.')
  if (!response.ok) throw new Error('Não foi possível carregar seu treino. Tente novamente.')
  const payload = await response.json() as { plan: CurrentTrainingPlan | null }
  return payload.plan
}

export async function getOwnTrainingDrafts(accessToken: string): Promise<TrainingPlanDraft[]> {
  const response = await fetch(`${apiBaseUrl}/training/drafts`, {
    headers: { Authorization: `Bearer ${accessToken}` },
  })
  if (response.status === 401) throw new Error('Sua sessão expirou. Entre novamente para continuar.')
  if (response.status === 403) throw new Error('Você não tem permissão para acessar seus rascunhos.')
  if (!response.ok) throw new Error('Não foi possível carregar seus rascunhos de treino. Tente novamente.')
  return response.json() as Promise<TrainingPlanDraft[]>
}
