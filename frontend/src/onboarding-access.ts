export type InvitationAccessStatus = 'valid' | 'expired' | 'invalid' | 'redeemed'

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

async function accessRequest(path: string, token: string, method = 'GET'): Promise<InvitationAccessStatus> {
  const response = await fetch(`${apiBaseUrl}${path}`, { method, headers: { 'X-Onboarding-Token': token } })
  if (!response.ok) throw new Error('Não foi possível validar este convite. Tente novamente mais tarde.')
  const body = (await response.json()) as { status?: InvitationAccessStatus }
  if (!body.status || !['valid', 'expired', 'invalid', 'redeemed'].includes(body.status)) {
    throw new Error('Não foi possível validar este convite. Tente novamente mais tarde.')
  }
  return body.status
}

export function validateOnboardingInvitation(token: string): Promise<InvitationAccessStatus> {
  return accessRequest('/onboarding/access', token)
}

export function redeemOnboardingInvitation(token: string): Promise<InvitationAccessStatus> {
  return accessRequest('/onboarding/access/redemptions', token, 'POST')
}
