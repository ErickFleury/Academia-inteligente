const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'

export type Occupancy = { occupancy: number; status: 'current' | 'stale'; updated_at: string | null }

export async function getOccupancy(): Promise<Occupancy> {
  const response = await fetch(`${apiBaseUrl}/occupancy`)
  if (!response.ok) throw new Error('Não foi possível consultar a ocupação agora. Tente novamente.')
  return response.json() as Promise<Occupancy>
}
