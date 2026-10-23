export type AssistantClarification = {
  reason: 'missing_client_information' | 'insufficient_evidence' | 'conflicting_evidence' | 'unsupported_guidance' | 'unspecified'
  stage: 'router' | 'retrieval' | 'specialist' | 'review'
  explanation: string
  next_step: string
}

export function clarificationMessage(value: unknown, fallback: string): string {
  if (!value || typeof value !== 'object') return fallback
  const { explanation, next_step: nextStep } = value as Partial<AssistantClarification>
  if (typeof explanation !== 'string' || !explanation.trim() || explanation.length > 500
    || typeof nextStep !== 'string' || !nextStep.trim() || nextStep.length > 400) return fallback
  return `${explanation.trim()} ${nextStep.trim()}`
}
