import type { RegistrationProof } from './biometrics'

export type ClientInput = {
  first_name: string
  surname: string
  email: string
  cpf: string
  phone: string
  postal_code: string
  street: string
  number: string
  complement: string | null
  neighborhood: string
  city: string
  state: string
}

export type Client = ClientInput & {
  id: string
  person_id: string
  name: string
  client_active: boolean
  identity_provisioned?: boolean
  created_at: string
}

export type CepAddress = Pick<ClientInput, 'street' | 'neighborhood' | 'city' | 'state'>

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

export class ApiRequestError extends Error {
  constructor(message: string, readonly status: number) { super(message) }
}

async function request<T>(accessToken: string, path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${apiBaseUrl}${path}`, { ...init, headers: { Authorization: `Bearer ${accessToken}`, 'Content-Type': 'application/json', ...init?.headers } })
  if (!response.ok) {
    const body = (await response.json().catch(() => null)) as { detail?: string } | null
    throw new ApiRequestError(body?.detail || 'Não foi possível concluir a solicitação.', response.status)
  }
  return response.status === 204 ? (undefined as T) : (response.json() as Promise<T>)
}

export function createClient(accessToken: string, data: ClientInput, proof: RegistrationProof): Promise<Client> {
  return request(accessToken, '/clients', { method: 'POST', body: JSON.stringify({ ...data, ...proof }) })
}
export function listClients(accessToken: string, query = ''): Promise<Client[]> {
  const search = query.trim() ? `?${new URLSearchParams({ query }).toString()}` : ''
  return request(accessToken, `/clients${search}`)
}
export function getClient(accessToken: string, clientId: string): Promise<Client> { return request(accessToken, `/clients/${clientId}`) }
export function lookupPostalCode(accessToken: string, postalCode: string): Promise<CepAddress> {
  return request(accessToken, `/clients/address-lookup?${new URLSearchParams({ postal_code: postalCode })}`)
}
export function provisionClientIdentity(accessToken: string, clientId: string): Promise<Client> { return request(accessToken, `/clients/${clientId}/provision-identity`, { method: 'POST' }) }
export function updateClient(accessToken: string, clientId: string, updates: Partial<ClientInput> & { client_active?: boolean }): Promise<Client> { return request(accessToken, `/clients/${clientId}`, { method: 'PATCH', body: JSON.stringify(updates) }) }
export function eraseClient(accessToken: string, clientId: string): Promise<void> { return request(accessToken, `/clients/${clientId}`, { method: 'DELETE' }) }
