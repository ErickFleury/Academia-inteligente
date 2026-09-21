export type TrainingExperience = 'none' | 'beginner' | 'intermediate' | 'advanced'

export type OnboardingDraft = {
  status: 'draft' | 'completed'
  training_goal: string | null
  training_experience: TrainingExperience | null
  height_cm: number | null
  weight_kg: string | number | null
  has_limitations_or_complaints: boolean | null
  limitations_or_complaints: string | null
  uses_medications: boolean | null
  medications: string | null
  has_health_conditions: boolean | null
  health_conditions: string | null
}

export type OnboardingDraftUpdate = Omit<OnboardingDraft, 'status'>

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

async function requestDraft(accessToken: string, method: 'GET' | 'PATCH', payload?: OnboardingDraftUpdate): Promise<OnboardingDraft> {
  const response = await fetch(`${apiBaseUrl}/onboarding/me`, {
    method,
    headers: {
      Authorization: `Bearer ${accessToken}`,
      ...(payload ? { 'Content-Type': 'application/json' } : {}),
    },
    ...(payload ? { body: JSON.stringify(payload) } : {}),
  })
  if (!response.ok) {
    if (response.status === 401) throw new Error('Sua sessão expirou. Entre novamente para continuar.')
    if (response.status === 403) throw new Error('Você não tem permissão para acessar este onboarding.')
    if (response.status === 409) throw new Error('Este onboarding já foi concluído e não pode ser alterado.')
    if (response.status === 422) throw new Error('Revise os campos informados antes de salvar.')
    throw new Error('Não foi possível salvar seu onboarding. Tente novamente.')
  }
  return response.json() as Promise<OnboardingDraft>
}

export function getOwnOnboardingDraft(accessToken: string): Promise<OnboardingDraft> {
  return requestDraft(accessToken, 'GET')
}

export function saveOwnOnboardingDraft(
  accessToken: string,
  payload: OnboardingDraftUpdate,
): Promise<OnboardingDraft> {
  return requestDraft(accessToken, 'PATCH', payload)
}
