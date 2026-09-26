const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'

export type ProfilePresence = { sharing_enabled: boolean; currently_present: boolean }

async function request(accessToken: string, options?: RequestInit): Promise<ProfilePresence> {
  const response = await fetch(`${apiBaseUrl}/profile-presence/me`, {
    ...options,
    headers: { Authorization: `Bearer ${accessToken}`, 'Content-Type': 'application/json', ...options?.headers },
  })
  if (!response.ok) throw new Error('Não foi possível atualizar a presença do perfil. Tente novamente.')
  return response.json() as Promise<ProfilePresence>
}

export function getOwnProfilePresence(accessToken: string): Promise<ProfilePresence> {
  return request(accessToken)
}

export function updateOwnProfilePresence(accessToken: string, enabled: boolean): Promise<ProfilePresence> {
  return request(accessToken, { method: 'PATCH', body: JSON.stringify({ enabled }) })
}
