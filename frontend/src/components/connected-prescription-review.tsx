import { useEffect, useState } from 'react'
import { Alert, Stack } from '@mui/material'

import { submitTrainingDraft, type TrainingPlanDraft } from '../training-plan'
import { assumePrescriptionManually, confirmPrescriptionInputs, getPrescriptionReview, type PrescriptionReviewState } from '../training-prescription'
import { TrainingPrescriptionReview } from './training-prescription-review'

type Props = {
  accessToken: string
  role: 'client' | 'instructor'
  versionId: string
  revision: number
  disabled?: boolean
  onSubmitted?: (draft: TrainingPlanDraft) => void
  onChanged?: () => Promise<void>
}

export function ConnectedPrescriptionReview({ accessToken, role, versionId, revision, disabled = false, onSubmitted, onChanged }: Props) {
  const [state, setState] = useState<PrescriptionReviewState>()
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [refresh, setRefresh] = useState(0)
  const [loadedFor, setLoadedFor] = useState('')
  const destination = `${role}:${versionId}:${revision}`
  const [requestScope, setRequestScope] = useState({ accessToken, destination, generation: 0 })
  if (requestScope.accessToken !== accessToken || requestScope.destination !== destination) {
    // Clear private state before paint; waiting for the request effect leaves
    // the previous session's review visible during the first committed render.
    setRequestScope({ accessToken, destination, generation: requestScope.generation + 1 })
    setState(undefined); setError(null); setLoadedFor(''); setLoading(true)
  }
  const target = `${requestScope.generation}:${destination}`

  useEffect(() => {
    let active = true
    setLoading(true); setError(null); setState(undefined); setLoadedFor('')
    void getPrescriptionReview(accessToken, role, versionId)
      .then((result) => { if (active) { setState(result); setLoadedFor(target) } })
      .catch((reason: unknown) => { if (active) setError(reason instanceof Error ? reason.message : 'Não foi possível carregar a revisão do treino.') })
      .finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [accessToken, role, versionId, revision, refresh, target])

  const visible = loadedFor === target ? state : undefined
  return <Stack spacing={2}>
    {error && <Alert severity="error">{error}</Alert>}
    {visible?.submitted_for_review && <Alert severity="info">Proposta enviada para revisão do instrutor.</Alert>}
    <TrainingPrescriptionReview key={target} role={role} loading={loading || disabled}
      outcome={visible?.outcome} savedDraft={visible?.saved_draft} confirmation={visible?.confirmation}
      onRetry={() => setRefresh((value) => value + 1)}
      onConfirm={async (hash) => { await confirmPrescriptionInputs(accessToken, versionId, hash); setRefresh((value) => value + 1) }}
      onSubmit={role === 'client' && !visible?.submitted_for_review ? async (id, expectedRevision) => {
        try { onSubmitted?.(await submitTrainingDraft(accessToken, id, expectedRevision)) }
        finally { setState(undefined); setRefresh((value) => value + 1) }
      } : undefined}
      onAssumeManual={role === 'instructor' ? async (id, expectedRevision, reason) => {
        try { await assumePrescriptionManually(accessToken, id, expectedRevision, reason); await onChanged?.() }
        finally { setState(undefined); setRefresh((value) => value + 1) }
      } : undefined} />
  </Stack>
}
