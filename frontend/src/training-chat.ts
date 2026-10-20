const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'

export type TrainingChatMessage = {
  role: 'user' | 'assistant'
  content: string
  created_at: string
  client_request_id?: string | null
  reply_to_client_request_id?: string | null
  adaptation_suggested?: boolean
  adaptation_reason?: string | null
  reference_citations?: { passage_id: string; title: string; version: number; location: string }[]
}

export type TrainingChat = { messages: TrainingChatMessage[] }

async function chatError(response: Response, fallback: string): Promise<never> {
  if (response.status === 401) throw new Error('Sua sessão expirou. Entre novamente para continuar.')
  if (response.status === 403) throw new Error('Você não tem permissão para acessar o assistente de treino.')
  if (response.status === 409) throw new Error('Seu treino, memória ou referências mudaram durante a resposta. Confira as informações e envie uma nova mensagem.')
  if (response.status === 422) {
    const data = await response.json().catch(() => ({}))
    if (data.detail === 'memory_capacity') throw new Error('Sua memória está cheia. Abra Memória do assistente para revisar as informações antes de continuar.')
    if (data.detail === 'assistant_clarification_required') throw new Error('Confirme as informações relevantes ou consulte seu instrutor antes de gerar a proposta.')
  }
  if (response.status === 503) throw new Error('O assistente de treino está indisponível no momento. Tente novamente.')
  throw new Error(fallback)
}

export async function getOwnTrainingChat(accessToken: string): Promise<TrainingChat> {
  const response = await fetch(`${apiBaseUrl}/training/chat`, {
    headers: { Authorization: `Bearer ${accessToken}` },
  })
  if (!response.ok) return chatError(response, 'Não foi possível carregar sua conversa. Tente novamente.')
  return response.json() as Promise<TrainingChat>
}

export async function sendTrainingChatMessage(
  accessToken: string,
  message: string,
  clientRequestId: string,
): Promise<TrainingChat> {
  const response = await fetch(`${apiBaseUrl}/training/chat/messages`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${accessToken}`, 'Content-Type': 'application/json' },
    body: JSON.stringify({ message, client_request_id: clientRequestId }),
  })
  if (!response.ok) return chatError(response, 'Não foi possível enviar sua mensagem. Tente novamente.')
  return response.json() as Promise<TrainingChat>
}
