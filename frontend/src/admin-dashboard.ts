const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'

export type ActiveClients = { active_clients: number }
export type AttendanceWeek = { week_start: string; confirmed_entries: number }
export type AttendanceHistory = { weeks: AttendanceWeek[] }
export type DashboardOccupancy = {
  occupancy: number
  status: 'current' | 'stale'
  updated_at: string | null
}

export class AdminDashboardRequestError extends Error {
  constructor(message: string, readonly status: number) {
    super(message)
  }
}

async function request<T>(accessToken: string, path: string): Promise<T> {
  const response = await fetch(`${apiBaseUrl}${path}`, {
    headers: { Authorization: `Bearer ${accessToken}` },
  })
  if (!response.ok) {
    const body = (await response.json().catch(() => null)) as { detail?: string } | null
    throw new AdminDashboardRequestError(
      body?.detail ?? 'Não foi possível carregar este indicador.',
      response.status,
    )
  }
  return response.json() as Promise<T>
}

export function getActiveClients(accessToken: string): Promise<ActiveClients> {
  return request(accessToken, '/admin/dashboard/active-clients')
}

export function getAttendanceHistory(accessToken: string): Promise<AttendanceHistory> {
  return request(accessToken, '/admin/dashboard/attendance')
}

export function getDashboardOccupancy(accessToken: string): Promise<DashboardOccupancy> {
  return request(accessToken, '/admin/dashboard/occupancy')
}
