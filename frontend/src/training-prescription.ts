import type { TrainingKnowledge } from './training-knowledge'
import type { DoseDetails } from './training-dose'

export type PrescriptionProjection = {
  name: string
  objective: string
  items: {
    exercise_name: string; sets: number | null; repetitions: string; load_guidance: string
    rest_seconds: number | null; dose_details?: DoseDetails | null; equipment_requirement?: string | null; equipment_model_id?: string | null
  }[]
}
export type PrescriptionReason = 'restriction_conflict' | 'missing_input' | 'insufficient_support' | 'technical_unavailability'
export type PrescriptionIssue = { item_id?: string; position?: number; field?: string; exercise_name?: string; reason: string; allowed?: string[] | { minimum: string | number | null; maximum: string | number | null; minimum_inclusive: boolean | null; maximum_inclusive: boolean | null } }
export function prescriptionIssueMessage(issue: PrescriptionIssue) {
  const labels: Record<string, string> = { sets: 'Séries', repetitions: 'Repetições', duration_seconds: 'Duração em segundos', duration_minutes: 'Duração em minutos', holds: 'Sustentações', hold_seconds: 'Segundos por sustentação', duration_seconds_per_side: 'Duração por lado', attempts: 'Tentativas', 'calculated_load.claimed_kg': 'Carga calculada', rir: 'Repetições em reserva', rpe: 'Percepção de esforço', progression: 'Progressão' }
  const field = labels[issue.field ?? ''] ?? (issue.field?.includes('seconds') ? 'Descanso em segundos' : 'Parâmetro da proposta')
  const location = issue.position ? `Exercício ${issue.position}${issue.exercise_name ? ` (${issue.exercise_name})` : ''}: ` : ''
  const bounds = Array.isArray(issue.allowed) ? undefined : issue.allowed
  const range = bounds ? [bounds.minimum !== null ? `${bounds.minimum_inclusive ? 'pelo menos' : 'mais de'} ${String(bounds.minimum).replace('.', ',')}` : '', bounds.maximum !== null ? `${bounds.maximum_inclusive ? 'no máximo' : 'menos de'} ${String(bounds.maximum).replace('.', ',')}` : ''].filter(Boolean).join(' e ') : ''
  return `${location}${field} precisa de correção${range ? `; permitido: ${range}` : ''}. Solicite uma nova verificação.`
}
export type PrescriptionTrace = {
  path: string; label_pt_br: string; rule_id: string; derivation: 'direct' | 'professionally_derived' | 'owner_derived'
  evidence: { source_id: string; passage_id: string; locator: string; outcome: string; certainty: string }[]
}
export type ValidatedPrescription = TrainingKnowledge & {
  prescription_eligibility: 'eligible'
  scope: 'session_sheet' | 'plan_revision'
  projection: PrescriptionProjection
  policy_version?: string
  validator_version?: string
  approval_basis?: 'owner_decision' | 'independent_review'
  professional_review_performed?: boolean
  trace?: PrescriptionTrace[]
  instructions: {
    session_id: string; item_id: string; progression: string; amount: string
    unit: 'kg' | 'repetitions' | 'seconds' | 'sets'; stop: string; regression: string; notes: string[]
  }[]
}
export type PrescriptionOutcome =
  | { status: 'accepted'; version_id: string; revision: number; requires_instructor_review: boolean; prescription: ValidatedPrescription }
  | { status: 'rejected'; category: PrescriptionReason; reason_codes: string[]; message: string; next_action?: 'clarify' | 'abstain' | 'stop' | 'regress'; issues?: PrescriptionIssue[] }
export type SavedPrescriptionDraft = {
  id: string; revision: number; qualification: 'legacy' | 'edited' | 'stale' | 'manual'
  projection: PrescriptionProjection
}
export type PrescriptionInputConfirmation = {
  id: string; label: string; value: string
}

export type PrescriptionReviewState = {
  submitted_for_review?: boolean
  outcome?: PrescriptionOutcome
  saved_draft?: SavedPrescriptionDraft
  confirmation?: { snapshotHash: string; facts: PrescriptionInputConfirmation[] }
}

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'
const reasonMessages: Record<PrescriptionReason, string> = {
  restriction_conflict: 'A proposta conflita com uma restrição revisada. Peça uma avaliação ao instrutor.',
  missing_input: 'Faltam informações confirmadas para este pedido. Revise os dados com o instrutor.',
  insufficient_support: 'Não foi possível gerar uma proposta com evidências suficientes para este pedido. Peça ao instrutor uma avaliação e a elaboração do treino.',
  technical_unavailability: 'Não foi possível consultar os serviços de treino agora. Tente novamente ou peça ao instrutor a elaboração do treino.',
}

export class PrescriptionInputRequiredError extends Error {}
export type RequestInputRequirements = {
  snapshot_hash: string
  requirements: { key: string; label: string; source: 'request' | 'onboarding'; can_provide: boolean; value: string | number | boolean | null; value_type: 'boolean' | 'number' | 'text'; measurement?: Record<string, string | null> | null }[]
}
export const getRequestInputRequirements = async (token: string): Promise<RequestInputRequirements> => {
  const response = await fetch(`${apiBaseUrl}/training/prescription/inputs`, { headers: { Authorization: `Bearer ${token}` }, cache: 'no-store' })
  if (!response.ok) throw new Error('As informações deste pedido não estão disponíveis para confirmação.')
  return response.json() as Promise<RequestInputRequirements>
}
export async function saveRequestInputs(token: string, body: object) {
  const response = await fetch(`${apiBaseUrl}/training/prescription/inputs`, { method: 'POST', headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' }, body: JSON.stringify(body) })
  if (!response.ok) throw new Error('Não foi possível registrar as informações. Recarregue e confira os dados; algumas observações exigem o instrutor.')
}

export function prescriptionRejectionMessage(detail: unknown): string | undefined {
  if (!detail || typeof detail !== 'object' || !('category' in detail)) return undefined
  const category = detail.category
  if (category === 'missing_input' && 'reason_codes' in detail && Array.isArray(detail.reason_codes)) {
    if (detail.reason_codes.includes('weekly_schedule_missing')) return 'Confirme a programação semanal deste pedido antes de gerar a proposta.'
    if (detail.reason_codes.includes('goal_priority_confirmation_required')) return 'Confirme o objetivo e suas prioridades com o instrutor antes de gerar esta proposta.'
  }
  return typeof category === 'string' && Object.hasOwn(reasonMessages, category)
    ? reasonMessages[category as PrescriptionReason] : undefined
}

async function prescriptionRequest(accessToken: string, path: string, body?: object) {
  const response = await fetch(`${apiBaseUrl}/training/${path}`, {
    method: body ? 'POST' : 'GET',
    headers: { Authorization: `Bearer ${accessToken}`, ...(body ? { 'Content-Type': 'application/json' } : {}) },
    ...(body ? { body: JSON.stringify(body) } : {}),
  })
  if (response.status === 401) throw new Error('Sua sessão expirou. Entre novamente para continuar.')
  if (response.status === 403 || response.status === 404) throw new Error('Você não tem acesso a esta revisão de treino.')
  if (!response.ok) {
    let detail: unknown
    try { detail = (await response.json() as { detail?: unknown }).detail } catch { /* Controlled fallback. */ }
    throw new Error(prescriptionRejectionMessage(detail) ?? 'Não foi possível concluir a revisão. Recarregue os dados e tente novamente.')
  }
  return response.json() as Promise<PrescriptionReviewState>
}

export function getPrescriptionReview(accessToken: string, role: 'client' | 'instructor', id: string) {
  return prescriptionRequest(accessToken, `${role === 'client' ? 'drafts' : 'pending'}/${encodeURIComponent(id)}/prescription`)
}

export async function confirmPrescriptionInputs(accessToken: string, id: string, snapshotHash: string) {
  await prescriptionRequest(accessToken, `drafts/${encodeURIComponent(id)}/prescription/confirm`, { expected_snapshot_hash: snapshotHash })
}

export async function assumePrescriptionManually(accessToken: string, id: string, revision: number, reason: string) {
  await prescriptionRequest(accessToken, `pending/${encodeURIComponent(id)}/prescription/assume-manual`, { expected_revision: revision, reason })
}
