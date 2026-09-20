export type Client = {
  id: string
  name: string
  email: string
  account_active: boolean
  created_at: string
}

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

export class ApiRequestError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message)
  }
}

async function request<T>(accessToken: string, path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${apiBaseUrl}${path}`, {
    ...init,
    headers: {
      Authorization: `Bearer ${accessToken}`,
      'Content-Type': 'application/json',
      ...init?.headers,
    },
  })
  if (!response.ok) {
    const body = (await response.json().catch(() => null)) as { detail?: string } | null
    throw new ApiRequestError(body?.detail || 'Não foi possível concluir a solicitação.', response.status)
  }
  return response.json() as Promise<T>
}

export function createClient(accessToken: string, name: string, email: string): Promise<Client> {
  return request(accessToken, '/clients', {
    method: 'POST',
    body: JSON.stringify({ name, email }),
  })
}

export function listClients(accessToken: string, query = ''): Promise<Client[]> {
  const search = query.trim() ? `?${new URLSearchParams({ query }).toString()}` : ''
  return request(accessToken, `/clients${search}`)
}

export function getClient(accessToken: string, clientId: string): Promise<Client> {
  return request(accessToken, `/clients/${clientId}`)
}

export function updateClient(
  accessToken: string,
  clientId: string,
  updates: Pick<Client, 'name' | 'email' | 'account_active'>,
): Promise<Client> {
  return request(accessToken, `/clients/${clientId}`, {
    method: 'PATCH',
    body: JSON.stringify(updates),
  })
}
