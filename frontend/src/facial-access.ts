import { biometricRequest } from './biometrics'

export type Direction = 'entry' | 'exit'
export type AccessAttempt = {
  attempt_id: string; direction: Direction; status: string; result_code: string; captures: number
  expires_at: string; client_id: string | null; client_name: string | null
  release_request_id: string | null; release_mode: 'simulated' | null; can_retry: boolean
}
export type ClientAccessState = { client_id: string; client_name: string; inside: boolean; revision: number; client_active: boolean }
export type PassageResult = { status: 'confirmed'; attempt_id: string; passage_event_id: string; state: ClientAccessState; occupancy: number }
export type CorrectionResult = { status: 'corrected' | 'unchanged'; correction_id: string; state: ClientAccessState; occupancy: number }
export type FaceEvent = { id: string; kind: string; occurred_at: string; operation: string; result: string; client_id: string | null; person_name: string | null; direction: Direction | null; reason: string | null }
export type EventPage = { items: FaceEvent[]; next_cursor: string | null }
export type ProviderStatus = { mode: 'disabled' | 'pilot'; available: boolean; cleanup_pending: number }

export function captureAccess(token: string, attemptId: string, image: Blob, signal?: AbortSignal) {
  const data = new FormData()
  data.append('command_id', crypto.randomUUID())
  data.append('file', image, 'capture.jpg')
  return biometricRequest<AccessAttempt>(token, `/access-attempts/${attemptId}/capture`, data, signal)
}

export const operationLabels: Record<string, string> = {
  access_attempt: 'Tentativa iniciada', access_capture: 'Reconhecimento', access_cancel: 'Tentativa cancelada',
  access_invalidated: 'Autorização invalidada', access_recovery: 'Recuperação de tentativa',
  passage_confirm: 'Passagem confirmada', state_correction: 'Correção de presença',
  enrollment_session: 'Cadastro facial iniciado', enrollment_capture: 'Captura de cadastro',
  enrollment_attach: 'Cadastro facial vinculado', enrollment_revoke: 'Cadastro facial revogado',
  enrollment_cleanup: 'Limpeza do cadastro facial',
}
export const resultLabels: Record<string, string> = {
  created: 'Iniciado', authorized: 'Liberação simulada solicitada', passage_confirmed: 'Passagem confirmada',
  corrected: 'Presença corrigida', unchanged: 'Estado mantido', enabled: 'Cadastro habilitado', disabled: 'Cadastro desabilitado',
  enrollment_ready: 'Captura pronta', ready: 'Captura pronta', enrolled: 'Rosto cadastrado', cleaned: 'Limpeza concluída', deleted: 'Removido',
}
