import { Alert, Box, Button, Checkbox, FormControlLabel, Stack, TextField, Typography } from '@mui/material'
import { useId, useState } from 'react'

import type { PrescriptionInputConfirmation, PrescriptionOutcome, SavedPrescriptionDraft } from '../training-prescription'
import { prescriptionIssueMessage } from '../training-prescription'
import { TrainingExerciseTable } from './training-exercise-table'
import { trainingCount, trainingRest } from '../training-dose'
import { TrainingKnowledgeSources } from './training-knowledge-sources'
import { EmptyState, LoadingState, StatusNotice } from './ui'

type Props = {
  outcome?: PrescriptionOutcome
  savedDraft?: SavedPrescriptionDraft
  role: 'client' | 'instructor'
  loading?: boolean
  confirmation?: { snapshotHash: string; facts: PrescriptionInputConfirmation[] }
  onConfirm?: (snapshotHash: string) => Promise<void>
  onRetry?: () => void
  onSubmit?: (id: string, revision: number) => Promise<void>
  onAssumeManual?: (id: string, revision: number, reason: string) => Promise<void>
}
const reasonCopy = {
  restriction_conflict: 'A proposta conflita com uma restrição revisada. Peça uma avaliação ao instrutor.',
  missing_input: 'Faltam informações confirmadas para este pedido. Revise os dados com o instrutor.',
  insufficient_support: 'Não foi possível gerar uma proposta com evidências suficientes para este pedido. Peça ao instrutor uma avaliação e a elaboração do treino.',
  technical_unavailability: 'Não foi possível consultar os serviços de treino agora. Tente novamente ou peça ao instrutor a elaboração do treino.',
}
const qualificationCopy = {
  legacy: 'Este rascunho ainda não foi verificado pelos critérios atuais.',
  edited: 'O conteúdo foi editado e precisa de nova verificação para ser apresentado como proposta de IA.',
  stale: 'As informações ou fontes mudaram. Recarregue e solicite uma nova verificação.',
  manual: 'O instrutor assumiu este conteúdo manualmente. Ele não possui qualificação atual de IA.',
}
const unitLabels = { kg: 'kg', repetitions: 'repetições', seconds: 'segundos', sets: 'séries' }

export function TrainingPrescriptionReview({ outcome, savedDraft, role, loading = false, confirmation, onConfirm, onRetry, onSubmit, onAssumeManual }: Props) {
  const headingId = useId()
  const [confirmedHash, setConfirmedHash] = useState<string | null>(null)
  const [manualReason, setManualReason] = useState('')
  const [busy, setBusy] = useState(false)
  const [feedback, setFeedback] = useState<string | null>(null)
  const [completedAction, setCompletedAction] = useState<string | null>(null)
  const accepted = outcome?.status === 'accepted' ? outcome : undefined
  const validated = accepted?.prescription
  const renderRows = (items: NonNullable<typeof validated>['projection']['items']) => items.map((item, index) => [
    String(index + 1), item.exercise_name, trainingCount(item.sets), item.repetitions, item.load_guidance, trainingRest(item.rest_seconds, item.dose_details),
  ])

  async function act(action: () => Promise<void>, key: string, success: string) {
    if (busy || loading) return
    setBusy(true); setFeedback(null)
    try { await action(); setCompletedAction(key); setFeedback(success) }
    catch { setFeedback('Não foi possível concluir a ação. Recarregue os dados e tente novamente.') }
    finally { setBusy(false) }
  }

  return <Stack component="section" aria-labelledby={headingId} aria-busy={loading || busy} spacing={2} sx={{ minWidth: 0, overflowWrap: 'anywhere' }}>
    <Typography component="h2" variant="h3" id={headingId}>Proposta de treino</Typography>
    {loading && <LoadingState label="Verificando informações e fontes do treino…" />}
    {!loading && !outcome && !savedDraft && !confirmation && <EmptyState title="Nenhuma proposta para revisar" description="Solicite uma proposta ao assistente ou peça ao instrutor a elaboração do treino." />}
    {outcome?.status === 'rejected' && <Alert severity={outcome.category === 'technical_unavailability' ? 'info' : 'warning'}>
      {reasonCopy[outcome.category]}
      {outcome.category === 'technical_unavailability' && onRetry && <Button onClick={onRetry} disabled={loading || busy}>Tentar novamente</Button>}
    </Alert>}
    {outcome?.status === 'rejected' && outcome.issues?.map((issue, index) => <Typography key={index} variant="body2">{prescriptionIssueMessage(issue)}</Typography>)}
    {validated?.approval_basis === 'owner_decision' && <Alert severity="info">Regras autorizadas pelo proprietário. Sem parecer profissional registrado. A proposta ainda depende da revisão do instrutor.</Alert>}
    {confirmation && confirmation.facts.length > 0 && <Stack spacing={1} component="section" aria-label="Confirmação das informações">
      <Typography component="h3" variant="h4">Confira as informações deste pedido</Typography>
      <Box component="dl" sx={{ m: 0 }}>{confirmation.facts.map((fact) => <Box key={fact.id} sx={{ mb: 1 }}>
        <Typography component="dt" variant="subtitle2">{fact.label}</Typography>
        <Typography component="dd" sx={{ m: 0 }}>{fact.value}</Typography>
      </Box>)}</Box>
      <Typography variant="body2">Esta confirmação vale para o pedido e não altera seu onboarding.</Typography>
      <FormControlLabel label="Confirmo que estas informações estão corretas para este pedido" control={<Checkbox checked={confirmedHash === confirmation.snapshotHash} onChange={(_, checked) => setConfirmedHash(checked ? confirmation.snapshotHash : null)} disabled={loading || busy} />} />
      {onConfirm && <Button disabled={loading || busy || confirmedHash !== confirmation.snapshotHash || completedAction === `confirm:${confirmation.snapshotHash}`} onClick={() => void act(() => onConfirm(confirmation.snapshotHash), `confirm:${confirmation.snapshotHash}`, 'Informações confirmadas para este pedido.')} variant="contained">Confirmar informações</Button>}
    </Stack>}
    {accepted && validated && <Stack spacing={2}>
      <StatusNotice severity="info">Critérios verificados para esta proposta. A revisão do instrutor continua necessária; a ficha ainda não está aprovada nem ativa.</StatusNotice>
      <Typography>Objetivo: {validated.projection.objective}</Typography>
      <Typography variant="body2">{validated.scope === 'session_sheet' ? 'Verificação desta sessão; não representa a semana inteira.' : 'Verificação da revisão completa do plano e de sua programação.'}</Typography>
      <TrainingExerciseTable rows={renderRows(validated.projection.items)} />
      {validated.instructions.map((instruction) => <Stack key={`${instruction.session_id}:${instruction.item_id}`} spacing={0.5}>
        <Typography variant="subtitle2">Progressão condicional</Typography>
        <Typography variant="body2">{instruction.progression} Quantidade prevista: {instruction.amount.replace('.', ',')} {unitLabels[instruction.unit]}.</Typography>
        <Typography variant="body2">{instruction.stop}</Typography>
        <Typography variant="body2">{instruction.regression}</Typography>
        {instruction.notes.map((note, index) => <Typography key={index} variant="body2">{note}</Typography>)}
      </Stack>)}
      <TrainingKnowledgeSources {...validated} />
      {role === 'instructor' && validated.trace && <Stack component="section" aria-label="Fundamentação das decisões" spacing={1}>
        <Typography component="h3" variant="h4">Fundamentação das decisões</Typography>
        <Typography variant="caption">Versão da política revisada: {validated.policy_version}</Typography>
        {validated.trace.map((decision) => <Box key={decision.path} sx={{ borderLeft: '2px solid', borderColor: 'divider', pl: 1.5 }}>
          <Typography variant="body2">Decisão: {decision.label_pt_br}</Typography>
          <Typography variant="caption">Regra: {decision.rule_id} · {decision.derivation === 'direct' ? 'Achado direto' : 'Aplicação profissional derivada'}</Typography>
          {decision.evidence.map((reference) => <Typography key={`${reference.source_id}:${reference.passage_id}`} variant="body2">Fonte: {reference.source_id} · Trecho: {reference.locator} · Desfecho: {reference.outcome}</Typography>)}
        </Box>)}
      </Stack>}
      {role === 'client' && onSubmit && accepted.requires_instructor_review && <Button variant="contained" disabled={loading || busy || completedAction === `submit:${accepted.version_id}:${accepted.revision}`} onClick={() => void act(() => onSubmit(accepted.version_id, accepted.revision), `submit:${accepted.version_id}:${accepted.revision}`, 'Proposta enviada para revisão do instrutor. Ela ainda não está aprovada.')}>
        Enviar proposta para revisão do instrutor
      </Button>}
    </Stack>}
    {savedDraft && <Stack component="section" aria-label="Rascunho salvo anterior" spacing={1.5}>
      <Typography component="h3" variant="h4">Rascunho salvo anterior</Typography>
      <Alert severity="info">{qualificationCopy[savedDraft.qualification]} {outcome?.status === 'rejected' && 'Este é o conteúdo já salvo, preservado após a tentativa sem sucesso.'}</Alert>
      <TrainingExerciseTable rows={renderRows(savedDraft.projection.items)} />
      {role === 'instructor' && onAssumeManual && savedDraft.qualification !== 'manual' && <Stack spacing={1}>
        <Typography variant="body2">Ao assumir o rascunho manualmente, você registra sua responsabilidade e mantém o histórico da IA. A aprovação continua sendo uma ação separada.</Typography>
        <TextField label="Motivo da responsabilidade manual" helperText="Descreva a revisão sem reproduzir dados sensíveis desnecessários." value={manualReason} onChange={(event) => setManualReason(event.target.value)} disabled={loading || busy} multiline slotProps={{ htmlInput: { maxLength: 500 } }} />
        <Button disabled={loading || busy || !manualReason.trim() || completedAction === `manual:${savedDraft.id}:${savedDraft.revision}`} variant="outlined" onClick={() => void act(() => onAssumeManual(savedDraft.id, savedDraft.revision, manualReason.trim()), `manual:${savedDraft.id}:${savedDraft.revision}`, 'Responsabilidade manual registrada. Revise antes de aprovar o treino.')}>
          Assumir responsabilidade manual
        </Button>
      </Stack>}
    </Stack>}
    {feedback && <Box role="status"><Typography>{feedback}</Typography></Box>}
  </Stack>
}
