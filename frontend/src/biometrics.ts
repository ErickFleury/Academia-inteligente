import { ApiRequestError } from './clients'

export type EnrollmentStatus = { person_id: string | null; status: 'enabled' | 'missing_or_revoked'; revision: number; cleanup_pending: boolean }
export type EnrollmentSession = { session_id: string; status: 'awaiting_capture' | 'capturing' | 'ready' | 'rejected' | 'expired' | 'consumed'; result_code: string; expires_at: string }
export type EnrollmentProof = { binding: string; sessionId: string | null; expiresAt: string | null }
export type RegistrationProof = { command_id: string; enrollment_session_id: string | null }
const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

export function personBinding(email: string, cpf: string) { return `${email.trim().toLowerCase()}\n${cpf.replace(/\D/g, '')}` }
export function validProof(proof: EnrollmentProof | null, email: string, cpf: string) {
  return !!proof && proof.binding === personBinding(email, cpf) && (!proof.expiresAt || Date.parse(proof.expiresAt) > Date.now())
}

export async function biometricRequest<T>(token: string, path: string, body?: object | FormData, signal?: AbortSignal): Promise<T> {
  const multipart = body instanceof FormData
  const response = await fetch(`${apiBaseUrl}/biometrics${path}`, {
    method: body === undefined ? 'GET' : 'POST', signal,
    headers: { Authorization: `Bearer ${token}`, ...(multipart ? {} : { 'Content-Type': 'application/json' }) },
    body: body === undefined ? undefined : multipart ? body : JSON.stringify(body),
  })
  if (!response.ok) {
    const payload = await response.json().catch(() => null) as { detail?: unknown } | null
    throw new ApiRequestError(typeof payload?.detail === 'string' ? payload.detail : 'biometric_request_failed', response.status)
  }
  return response.json() as Promise<T>
}

export function captureEnrollment(token: string, sessionId: string, image: Blob, commandId: string, signal?: AbortSignal) {
  const data = new FormData()
  data.append('command_id', commandId)
  data.append('file', image, 'capture.jpg')
  return biometricRequest<EnrollmentSession>(token, `/enrollment-sessions/${sessionId}/capture`, data, signal)
}

const messages: Record<string, string> = {
  no_face: 'Nenhum rosto encontrado. Olhe para a câmera e tente novamente.',
  multiple_faces: 'Mantenha apenas um rosto no enquadramento.',
  face_quality_low: 'O rosto não ficou nítido. Melhore a iluminação e olhe para a câmera.',
  face_identity_conflict: 'Este rosto corresponde a outro cadastro ou a uma captura pendente. Confira a identidade antes de tentar novamente.',
  face_identity_ambiguous: 'A identificação ficou ambígua. Confira o cadastro e faça uma nova captura.',
  identity_conflict: 'O e-mail e o CPF pertencem a cadastros diferentes. Confira os dados.',
  identity_invalid: 'Informe um e-mail e um CPF válidos antes de verificar o rosto.',
  enrollment_required: 'Conclua a captura facial antes de finalizar o cadastro.',
  enrollment_not_ready: 'A captura ainda não está pronta ou expirou. Verifique o cadastro facial novamente.',
  enrollment_stale: 'O cadastro facial mudou. Atualize o estado antes de tentar novamente.',
  enrollment_identity_conflict: 'Os dados da pessoa mudaram. Verifique o cadastro facial novamente.',
  session_expired: 'A captura expirou. Inicie uma nova verificação facial.',
  session_not_found: 'Esta captura não está disponível nesta sessão de administrador.',
  session_not_capturable: 'Esta captura já foi processada. Consulte o resultado.',
  capture_in_progress: 'Há uma captura em andamento. Aguarde e tente novamente.',
  capture_interrupted: 'A captura foi interrompida. Você pode fazer uma nova captura.',
  capture_superseded: 'Uma captura mais recente substituiu esta solicitação.',
  capture_invalid: 'Não foi possível processar a imagem da câmera. Faça uma nova captura.',
  capture_size_invalid: 'A imagem excedeu o limite permitido. Reduza a resolução da câmera.',
  biometrics_unavailable: 'O reconhecimento facial está indisponível. O cadastro não foi concluído.',
  biometric_configuration_invalid: 'O serviço facial ainda não está configurado. Tente novamente após a configuração.',
  provider_unavailable: 'O serviço facial não respondeu. Consulte o resultado antes de fazer outra captura.',
  command_conflict: 'Esta solicitação já foi usada com outros dados. Atualize a página e confira o cadastro.',
}
export function biometricMessage(reason: unknown): string {
  const code = reason instanceof Error ? reason.message : String(reason)
  if (reason instanceof ApiRequestError && reason.status === 401) return 'Sua sessão expirou. Entre novamente.'
  if (reason instanceof ApiRequestError && reason.status === 403) return 'Somente administradores podem gerenciar o cadastro facial.'
  return messages[code] ?? 'Não foi possível concluir a operação facial. Seus dados do formulário foram preservados.'
}
export function isBiometricError(reason: unknown) { return reason instanceof Error && reason.message in messages }
