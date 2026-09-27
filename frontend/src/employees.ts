import { ApiRequestError, lookupPostalCode, type CepAddress, type ClientInput } from './clients'
import type { RegistrationProof } from './biometrics'

export type EmployeeInput = ClientInput & { cnpj: string | null; specialization: 'instructor' }
export type Employee = EmployeeInput & {
  id: string
  person_id: string
  name: string
  employee_active: boolean
  identity_provisioned: boolean
  created_at: string
}

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

async function request<T>(accessToken: string, path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${apiBaseUrl}${path}`, { ...init, headers: { Authorization: `Bearer ${accessToken}`, 'Content-Type': 'application/json', ...init?.headers } })
  if (!response.ok) {
    const body = (await response.json().catch(() => null)) as { detail?: string } | null
    throw new ApiRequestError(body?.detail || 'Não foi possível concluir a solicitação.', response.status)
  }
  return response.json() as Promise<T>
}

export function createEmployee(accessToken: string, data: EmployeeInput, proof: RegistrationProof): Promise<Employee> { return request(accessToken, '/employees', { method: 'POST', body: JSON.stringify({ ...data, ...proof }) }) }
export function listEmployees(accessToken: string, query = ''): Promise<Employee[]> { const search = query.trim() ? `?${new URLSearchParams({ query }).toString()}` : ''; return request(accessToken, `/employees${search}`) }
export function getEmployee(accessToken: string, id: string): Promise<Employee> { return request(accessToken, `/employees/${id}`) }
export function updateEmployee(accessToken: string, id: string, data: Partial<EmployeeInput> & { employee_active?: boolean }): Promise<Employee> { return request(accessToken, `/employees/${id}`, { method: 'PATCH', body: JSON.stringify(data) }) }
export function provisionEmployeeIdentity(accessToken: string, id: string): Promise<Employee> { return request(accessToken, `/employees/${id}/provision-identity`, { method: 'POST' }) }
export { lookupPostalCode, type CepAddress }
