const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'

export type CurrentTrainingItem = {
  exercise_name: string
  sets: number
  repetitions: string
  load_guidance: string
  rest_seconds: number
  position: number
}

export type CurrentTrainingPlan = {
  plan_id: string
  version_number: number
  status: 'current'
  name: string
  objective: string
  items: CurrentTrainingItem[]
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
