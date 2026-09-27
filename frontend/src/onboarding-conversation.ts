export type ConversationMessage = {
  role: 'user' | 'assistant'
  content: string
  created_at: string
}

export type OnboardingConversation = {
  messages: ConversationMessage[]
  missing_required_fields: string[]
  completion_ready: boolean
  known_answers?: Record<string, string | number | boolean | null>
  clarification_fields?: string[]
  needs_clarification?: boolean
  fallback_field?: string | null
}

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

async function requestConversation(
  accessToken: string,
  method: 'GET' | 'POST',
  payload?: { message: string; client_request_id: string },
): Promise<OnboardingConversation> {
  const response = await fetch(`${apiBaseUrl}/onboarding/conversation${method === 'POST' ? '/messages' : ''}`, {
    method,
    headers: {
      Authorization: `Bearer ${accessToken}`,
      ...(payload ? { 'Content-Type': 'application/json' } : {}),
    },
    ...(payload ? { body: JSON.stringify(payload) } : {}),
  })
  if (!response.ok) {
    if (response.status === 401) throw new Error('Sua sessão expirou. Entre novamente para continuar.')
    if (response.status === 403) throw new Error('Você não tem permissão para acessar esta conversa.')
    if (response.status === 503) throw new Error('A conversa está indisponível no momento. Tente novamente.')
    if (response.status === 409) throw new Error('Seu onboarding mudou. Atualize a página antes de continuar.')
    throw new Error('Não foi possível continuar a conversa. Tente novamente.')
  }
  return response.json() as Promise<OnboardingConversation>
}

export function getOwnOnboardingConversation(accessToken: string): Promise<OnboardingConversation> {
  return requestConversation(accessToken, 'GET')
}

export function sendOnboardingConversationMessage(
  accessToken: string,
  message: string,
  clientRequestId: string,
): Promise<OnboardingConversation> {
  return requestConversation(accessToken, 'POST', {
    message,
    client_request_id: clientRequestId,
  })
}
