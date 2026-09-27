const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'

export class PasswordRecoveryError extends Error {
  constructor(message: string, readonly status: number) { super(message) }
}

export async function requestPasswordRecovery(accessToken: string, clientId?: string): Promise<void> {
  const path = clientId ? `/clients/${encodeURIComponent(clientId)}/password-reset` : '/identity/me/password-reset'
  const response = await fetch(`${apiBaseUrl}${path}`, {
    method: 'POST', headers: { Authorization: `Bearer ${accessToken}` },
  })
  if (!response.ok) {
    const messages: Record<number, string> = {
      401: 'Sua sessão expirou. Entre novamente para continuar.',
      403: 'Você não tem permissão para solicitar esta redefinição.',
      404: 'O cadastro do cliente não foi encontrado.',
      409: 'O acesso da conta precisa estar ativo e sincronizado. Solicite ajuda à administração.',
      429: 'Aguarde um minuto antes de solicitar outro link.',
    }
    throw new PasswordRecoveryError(messages[response.status] ?? 'Não foi possível confirmar o envio. Verifique o e-mail cadastrado e aguarde um minuto antes de tentar novamente.', response.status)
  }
}
