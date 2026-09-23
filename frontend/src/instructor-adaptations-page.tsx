import { Box, Button, Card, CardContent, MenuItem, Stack, TextField, Typography } from '@mui/material'
import { useEffect, useState } from 'react'

import { ClientShell } from './components/application-shell'
import { EmptyState, LoadingState, PageHeader, StatusNotice } from './components/ui'
import {
  decideInstructorAdaptation,
  getInstructorAdaptations,
  updateInstructorAdaptation,
  type AdaptationOperationInput,
  type TrainingAdaptation,
} from './training-adaptation'

type Props = { accessToken: string; onSignOut: () => void }

type EditableProposal = {
  explanation: string
  operations: AdaptationOperationInput[]
}

function editable(proposal: TrainingAdaptation): EditableProposal {
  return {
    explanation: proposal.explanation,
    operations: proposal.operations.map((operation) => ({
      operation_type: operation.operation_type,
      target_position: operation.target_position,
      item: operation.operation_type === 'remove' ? null : {
        exercise_name: operation.exercise_name ?? '',
        sets: operation.sets ?? 1,
        repetitions: operation.repetitions ?? '',
        load_guidance: operation.load_guidance ?? '',
        rest_seconds: operation.rest_seconds ?? 0,
        equipment_requirement: operation.equipment_requirement ?? null,
        is_existing_exercise: operation.is_existing_exercise ?? false,
      },
    })),
  }
}

export function InstructorAdaptationsPage({ accessToken, onSignOut }: Props) {
  const [proposals, setProposals] = useState<TrainingAdaptation[] | null>(null)
  const [drafts, setDrafts] = useState<Record<string, EditableProposal>>({})
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let active = true
    void getInstructorAdaptations(accessToken)
      .then((items) => {
        if (!active) return
        setProposals(items)
        setDrafts(Object.fromEntries(items.map((item) => [item.id, editable(item)])))
      })
      .catch((reason: unknown) => active && setError(reason instanceof Error ? reason.message : 'Não foi possível carregar as propostas.'))
    return () => { active = false }
  }, [accessToken])

  function updateDraft(id: string, change: (draft: EditableProposal) => EditableProposal) {
    setDrafts((items) => ({ ...items, [id]: change(items[id]) }))
  }

  async function save(proposal: TrainingAdaptation) {
    const draft = drafts[proposal.id]
    try {
      const updated = await updateInstructorAdaptation(accessToken, proposal.id, draft.explanation, draft.operations)
      setProposals((items) => items?.map((item) => item.id === updated.id ? updated : item) ?? null)
      setDrafts((items) => ({ ...items, [updated.id]: editable(updated) }))
    } catch (reason) { setError(reason instanceof Error ? reason.message : 'Não foi possível salvar a revisão.') }
  }

  async function decide(proposal: TrainingAdaptation, approve: boolean) {
    try {
      const updated = await decideInstructorAdaptation(accessToken, proposal.id, approve)
      setProposals((items) => items?.filter((item) => item.id !== updated.id) ?? null)
    } catch (reason) { setError(reason instanceof Error ? reason.message : 'Não foi possível concluir a revisão.') }
  }

  if (!proposals) return <ClientShell onSignOut={onSignOut}><LoadingState label="Carregando propostas para revisão" /></ClientShell>

  return <ClientShell onSignOut={onSignOut}>
    <Stack spacing={3} sx={{ maxWidth: 980 }}>
      <PageHeader eyebrow="Revisão profissional" title="Propostas de alteração" description="Revise e ajuste as sugestões antes de aprovar uma nova ficha. A aprovação cria uma nova versão atual." />
      {error && <StatusNotice severity="error">{error}</StatusNotice>}
      {proposals.length === 0 && <EmptyState title="Nenhuma proposta pendente" description="Quando um cliente aceitar uma proposta, ela aparecerá aqui para sua revisão." />}
      {proposals.map((proposal) => {
        const draft = drafts[proposal.id]
        return <Card key={proposal.id}><CardContent><Stack spacing={2}>
          <Typography component="h2" variant="h3">Solicitação: {proposal.reason}</Typography>
          <Typography color="text.secondary">Plano-base</Typography>
          <Typography>{proposal.base_items.map((item) => `${item.position}. ${item.exercise_name} — ${item.sets}×${item.repetitions}`).join(' · ')}</Typography>
          <TextField fullWidth label="Explicação para o cliente" multiline value={draft.explanation} onChange={(event) => updateDraft(proposal.id, (value) => ({ ...value, explanation: event.target.value }))} />
          {draft.operations.map((operation, index) => <Card key={index} variant="outlined"><CardContent><Stack spacing={1.25}>
            <TextField select label="Operação" value={operation.operation_type} onChange={(event) => updateDraft(proposal.id, (value) => ({ ...value, operations: value.operations.map((item, position) => position === index ? { ...item, operation_type: event.target.value as AdaptationOperationInput['operation_type'], item: event.target.value === 'remove' ? null : item.item ?? { exercise_name: '', sets: 1, repetitions: '', load_guidance: '', rest_seconds: 0, equipment_requirement: null, is_existing_exercise: false } } : item) }))}>
              <MenuItem value="add">Adicionar exercício</MenuItem><MenuItem value="remove">Remover exercício</MenuItem><MenuItem value="replace">Substituir exercício</MenuItem><MenuItem value="adjust">Ajustar prescrição</MenuItem>
            </TextField>
            {operation.operation_type !== 'add' && <TextField label="Posição afetada" type="number" value={operation.target_position ?? ''} onChange={(event) => updateDraft(proposal.id, (value) => ({ ...value, operations: value.operations.map((item, position) => position === index ? { ...item, target_position: Number(event.target.value) || null } : item) }))} />}
            {operation.item && <><TextField label="Exercício" value={operation.item.exercise_name} onChange={(event) => updateDraft(proposal.id, (value) => ({ ...value, operations: value.operations.map((item, position) => position === index && item.item ? { ...item, item: { ...item.item, exercise_name: event.target.value } } : item) }))} /><Stack direction={{ xs: 'column', sm: 'row' }} spacing={1}><TextField fullWidth label="Séries" type="number" value={operation.item.sets} onChange={(event) => updateDraft(proposal.id, (value) => ({ ...value, operations: value.operations.map((item, position) => position === index && item.item ? { ...item, item: { ...item.item, sets: Number(event.target.value) } } : item) }))} /><TextField fullWidth label="Repetições" value={operation.item.repetitions} onChange={(event) => updateDraft(proposal.id, (value) => ({ ...value, operations: value.operations.map((item, position) => position === index && item.item ? { ...item, item: { ...item.item, repetitions: event.target.value } } : item) }))} /></Stack><TextField label="Orientação de carga" value={operation.item.load_guidance} onChange={(event) => updateDraft(proposal.id, (value) => ({ ...value, operations: value.operations.map((item, position) => position === index && item.item ? { ...item, item: { ...item.item, load_guidance: event.target.value } } : item) }))} /></>}
            <Box><Button color="error" onClick={() => updateDraft(proposal.id, (value) => ({ ...value, operations: value.operations.filter((_, position) => position !== index) }))}>Excluir operação</Button></Box>
          </Stack></CardContent></Card>)}
          <Button onClick={() => updateDraft(proposal.id, (value) => ({ ...value, operations: [...value.operations, { operation_type: 'add', target_position: null, item: { exercise_name: '', sets: 1, repetitions: '', load_guidance: '', rest_seconds: 0, equipment_requirement: null, is_existing_exercise: false } }] }))} variant="outlined">Adicionar operação</Button>
          <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1}><Button onClick={() => void save(proposal)} variant="outlined">Salvar revisão</Button><Button onClick={() => void decide(proposal, true)} variant="contained">Aprovar e ativar</Button><Button color="error" onClick={() => void decide(proposal, false)}>Recusar proposta</Button></Stack>
        </Stack></CardContent></Card>
      })}
    </Stack>
  </ClientShell>
}
