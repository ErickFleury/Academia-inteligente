export type ReviewFunction = 'methodological' | 'professional' | 'adjudicator'
export type ReviewDecision = 'approved' | 'changes_requested' | 'rejected'
export type Certainty = 'not_assessed' | 'very_low' | 'low' | 'moderate' | 'high'
export type DomainJudgment = { domain: string; judgment: string; source_locator: string }
export type OutcomeCertainty = { outcome: string; certainty: Certainty; rationale: string }
export type JudgmentInput = {
  request_id: string; expected_artifact_sha256: string; function: ReviewFunction
  decision: ReviewDecision; scope: string; method_and_version: string; rationale: string
  competence: string; conflicts: string; judgments: DomainJudgment[]; outcomes: OutcomeCertainty[]
  personally_performed: boolean; resolves_judgment_ids: string[]
  independent_assessment?: boolean
  supersedes_judgment_id?: string | null; review_due_at?: string | null
}
export type EvidenceJudgment = {
  id: string; artifact_id: string; artifact_sha256: string; reviewer_name: string
  function: ReviewFunction; decision: ReviewDecision; created_at: string
  assessment: Omit<JudgmentInput, 'request_id' | 'expected_artifact_sha256'>
  is_current: boolean; can_supersede: boolean
  human_review_record: Record<string, unknown>
}
export type EvidenceArtifact = {
  id: string; kind: 'source' | 'rule_proposal' | 'prescription_bundle' | 'evaluation_protocol'; title: string; sha256: string
  approval_ready: boolean; missing_items: string[]; independence_complete: boolean
  owner_approval?: { decision_id: string; authority: 'project_owner'; decided_on: string; professional_review_performed: false; independent_evaluation_performed: false } | null
  sections: { label: string; text: string }[]; content: Record<string, unknown> | null
  judgments: EvidenceJudgment[]
}
export type EvaluationProtocol = {
  title: string; scope: string; methods: string; decision_thresholds: string
  repeat_count: number; maximum_writer_calls: number; maximum_runtime_seconds: number
}
export type SealedCase = {
  case_id: string; cohort: string; scenario: string; reference_judgment: string; critical: boolean
}
export type SealInput = {
  request_id: string; artifact_hashes: Record<string, string>; protocol: EvaluationProtocol
  cases: SealedCase[]; synthetic_only: boolean; independent_and_unexposed: boolean
  understands_no_release: boolean
}
export type EvidenceSeal = {
  id: string; custodian_name: string; protocol: EvaluationProtocol
  artifact_hashes: Record<string, string>; case_count: number; payload_sha256: string
  created_at: string; can_read_cases: boolean
  status: 'custody_registered_evaluation_and_release_pending'
}
export type SealCases = { id: string; payload_sha256: string; cases: SealedCase[] }

export const reviewFunctionLabels: Record<ReviewFunction, string> = {
  methodological: 'Revisão metodológica', professional: 'Revisão profissional', adjudicator: 'Resolução de divergência',
}
export const reviewDecisionLabels: Record<ReviewDecision, string> = {
  approved: 'Aprovar o conteúdo revisado', changes_requested: 'Solicitar alterações', rejected: 'Rejeitar o conteúdo',
}
export const certaintyLabels: Record<Certainty, string> = {
  not_assessed: 'Não avaliada', very_low: 'Muito baixa', low: 'Baixa', moderate: 'Moderada', high: 'Alta',
}

const messages: Record<string, string> = {
  active_instructor_required: 'É necessário um perfil de instrutor ativo para revisar evidências.',
  review_artifact_not_found: 'O artefato de revisão não foi encontrado.',
  review_record_not_found: 'O parecer solicitado não foi encontrado.',
  review_artifact_changed: 'O conteúdo mudou. Recarregue a versão antes de registrar o parecer.',
  review_artifact_incomplete: 'O contrato está incompleto. Registre as alterações necessárias antes de aprová-lo.',
  one_independent_review_per_person: 'Use a substituição para corrigir seu parecer. As funções independentes precisam de pessoas distintas.',
  review_request_conflict: 'Esta solicitação já foi usada com outro conteúdo. Recarregue os registros.',
  review_registration_conflict: 'Já existe um parecer seu para esta versão. Recarregue os registros.',
  adjudication_references_invalid: 'Selecione os pareceres metodológico e profissional desta versão para resolver a divergência.',
  seal_request_conflict: 'Esta solicitação de custódia já foi usada com outro conteúdo. Recarregue os registros.',
  seal_registration_conflict: 'A custódia já foi registrada. Recarregue a lista antes de tentar novamente.',
  seal_not_found: 'Os casos não estão disponíveis para sua conta.',
  review_artifacts_unavailable: 'Os artefatos de revisão estão indisponíveis. Tente novamente mais tarde.',
  review_storage_unavailable: 'Não foi possível acessar os registros de revisão. Tente novamente mais tarde.',
  review_record_too_large: 'O registro ultrapassa o limite de tamanho. Reduza o conteúdo antes de enviar.',
  sealed_payload_integrity_error: 'Não foi possível verificar a integridade dos casos. Preserve o registro e solicite uma revisão técnica.',
}
export class EvidenceReviewError extends Error {
  constructor(readonly status: number, message: string) { super(message) }
}
const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'
async function request<T>(token: string, path: string, body?: object): Promise<T> {
  const response = await fetch(`${apiBaseUrl}/training/evidence-review/${path}`, {
    method: body ? 'POST' : 'GET', cache: 'no-store',
    headers: { Authorization: `Bearer ${token}`, ...(body ? { 'Content-Type': 'application/json' } : {}) },
    ...(body ? { body: JSON.stringify(body) } : {}),
  })
  if (!response.ok) {
    const error = await response.json().catch(() => ({}))
    const message = response.status === 401 ? 'Sua sessão expirou. Entre novamente.'
      : response.status === 403 ? 'Seu perfil não tem permissão para revisar estas evidências.'
        : typeof error.detail === 'string' && messages[error.detail] ? messages[error.detail]
          : response.status === 422 ? 'Revise os campos, as declarações e o orçamento informado.'
            : 'Não foi possível concluir a operação. Tente novamente.'
    throw new EvidenceReviewError(response.status, message)
  }
  return response.json() as Promise<T>
}
export const listEvidenceArtifacts = (token: string) => request<EvidenceArtifact[]>(token, 'artifacts')
export type EvidenceReadiness = {
  owner_rag?: { enabled: boolean; authorized: boolean; independent_evaluation_required: boolean }
  rules: { rule_id: string; owner_accepted: boolean; executable_policy_ids: string[] }[]
  profiles: { goal_family: string; compiled_policy_ids: string[] }[]
  missing_items: string[]
  enabled_cohorts: string[]
}
export const getEvidenceReadiness = (token: string) => request<EvidenceReadiness>(token, 'readiness')
export const getEvidenceArtifact = (token: string, id: string) => request<EvidenceArtifact>(token, `artifacts/${encodeURIComponent(id)}`)
export const submitEvidenceJudgment = (token: string, id: string, body: JudgmentInput) => request<EvidenceJudgment>(token, `artifacts/${encodeURIComponent(id)}/judgments`, body)
export const listEvidenceSeals = (token: string) => request<EvidenceSeal[]>(token, 'seals')
export const submitEvidenceSeal = (token: string, body: SealInput) => request<EvidenceSeal>(token, 'seals', body)
export const getEvidenceSealCases = (token: string, id: string) => request<SealCases>(token, `seals/${encodeURIComponent(id)}/cases`)
