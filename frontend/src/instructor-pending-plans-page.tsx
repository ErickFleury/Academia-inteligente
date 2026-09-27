import { Box, Button, Card, CardContent, Stack, Typography } from '@mui/material'
import { useEffect, useRef, useState } from 'react'
import { useSearchParams } from 'react-router-dom'

import { ApiRequestError } from './clients'
import { EmptyState, LoadingState, PageHeader, StatusNotice } from './components/ui'
import { TrainingDraftFields } from './training-draft-fields'
import { InstructorShell } from './instructor-shell'
import { approvePendingPlan, getPendingPlan, getPendingPlans, savePendingPlan, type PendingPlan, type ReviewContent } from './training-review'

const sources = { ai: 'IA', instructor: 'Instrutor', adaptation: 'Adaptação aceita pelo cliente' }
const date = (value: string) => new Date(value).toLocaleString('pt-BR')
const content = (plan: PendingPlan): ReviewContent => ({ name: plan.name, objective: plan.objective, items: plan.items.map((item) => ({ exercise_name: item.exercise_name, sets: item.sets, repetitions: item.repetitions, load_guidance: item.load_guidance, rest_seconds: item.rest_seconds, equipment_requirement: item.equipment_requirement ?? null, equipment_model_id: item.equipment_model_id ?? null })) })

export function InstructorPendingPlansPage({ accessToken, onSignOut }: { accessToken: string; onSignOut: () => void }) {
  const [searchParams] = useSearchParams()
  const requestedDraft = searchParams.get('rascunho')
  const [plans, setPlans] = useState<PendingPlan[]>([])
  const [nextOffset, setNextOffset] = useState<number | null>(null)
  const [loading, setLoading] = useState(true)
  const [selected, setSelected] = useState<PendingPlan | null>(null)
  const [draft, setDraft] = useState<ReviewContent | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const [stale, setStale] = useState(false)
  const [busy, setBusy] = useState(false)
  const working = useRef(false)
  const editorHeading = useRef<HTMLHeadingElement>(null)
  useEffect(() => {
    if (selected) {
      editorHeading.current?.focus()
      editorHeading.current?.scrollIntoView?.({ block: 'start' })
    }
  }, [selected?.id])

  function failure(reason: unknown) {
    setError(reason instanceof ApiRequestError ? reason.message : 'Não foi possível carregar ou salvar os planos. Tente novamente.')
    if (reason instanceof ApiRequestError && [404, 409].includes(reason.status)) setStale(true)
  }
  async function load(offset = 0) {
    setLoading(true)
    setError(null)
    try {
      const page = await getPendingPlans(accessToken, offset)
      setPlans((previous) => offset === 0 ? page.items : [...previous, ...page.items.filter((item) => !previous.some((old) => old.id === item.id))])
      setNextOffset(page.next_offset)
    } catch (reason) { failure(reason) }
    finally { setLoading(false) }
  }
  useEffect(() => { void load() }, [accessToken])
  useEffect(() => {
    if (requestedDraft) void open({ id: requestedDraft })
  }, [accessToken, requestedDraft])

  async function open(plan: Pick<PendingPlan, 'id'>) {
    if (working.current) return
    working.current = true; setBusy(true); setError(null); setNotice(null)
    try {
      const latest = await getPendingPlan(accessToken, plan.id)
      setSelected(latest); setDraft(content(latest)); setStale(false)
    } catch (reason) { failure(reason) }
    finally { working.current = false; setBusy(false) }
  }
  async function submit(plan: PendingPlan, approve: boolean, changes?: ReviewContent) {
    if (working.current || stale) return
    working.current = true; setBusy(true); setError(null); setNotice(null)
    try {
      let latest = plan
      if (changes) {
        const saved = await savePendingPlan(accessToken, plan, changes)
        latest = { ...plan, ...saved }
        setSelected(latest); setDraft(content(latest))
        setPlans((items) => items.map((item) => item.id === plan.id ? latest : item))
      }
      if (approve) {
        await approvePendingPlan(accessToken, latest)
        setSelected(null); setDraft(null)
        await load()
      }
      setNotice(approve ? 'Plano aprovado e definido como treino atual.' : 'Rascunho salvo. O treino atual não foi alterado.')
    } catch (reason) { failure(reason) }
    finally { working.current = false; setBusy(false) }
  }
  return <InstructorShell onSignOut={onSignOut}><Stack spacing={3}>
    <PageHeader eyebrow="Revisão profissional" title="Planos pendentes" description="Revise o rascunho completo. Salvar não altera o treino atual; aprovar torna esta versão o treino atual do cliente." />
    {error && <StatusNotice severity="error">{error}</StatusNotice>}
    {notice && <StatusNotice severity="success">{notice}</StatusNotice>}
    <Box><Button disabled={busy || loading} onClick={() => { setSelected(null); setDraft(null); setStale(false); void load() }} variant="outlined">Recarregar lista</Button></Box>
    {loading && <LoadingState label="Carregando planos pendentes" />}
    {!loading && !error && plans.length === 0 && <EmptyState title="Nenhum plano pendente" description="Os rascunhos aguardando aprovação aparecerão aqui." />}
    {plans.map((plan) => <Card component="article" key={plan.id}><CardContent><Stack spacing={1.5}>
      <Typography component="h2" variant="h3" sx={{ overflowWrap: 'anywhere' }}>{plan.client_name}</Typography>
      <Typography sx={{ overflowWrap: 'anywhere' }}>{plan.name}</Typography>
      <Typography color="text.secondary">Origem: {sources[plan.source]} · Revisão {plan.revision}</Typography>
      <Typography color="text.secondary" variant="body2">Criado em {date(plan.created_at)} · Atualizado em {date(plan.updated_at)}</Typography>
      <Typography variant="body2">Instrutor responsável pelo treino atual: {plan.current_responsible_instructor_name ?? 'Não informado'}</Typography>
      <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1}>
        <Button disabled={busy} onClick={() => void open(plan)} variant="outlined">Editar e aprovar</Button>
        <Button disabled={busy || stale || selected !== null} onClick={() => void submit(plan, true)} variant="contained">Aprovar</Button>
      </Stack>
    </Stack></CardContent></Card>)}
    {nextOffset !== null && <Button disabled={loading || busy} onClick={() => void load(nextOffset)}>Carregar mais planos</Button>}
    {selected && draft && <Card component="section"><CardContent><Stack spacing={2}>
      <Typography component="h2" ref={editorHeading} tabIndex={-1} variant="h3" sx={{ scrollMarginTop: { xs: 88, md: 16 } }}>Revisar plano de {selected.client_name}</Typography>
      <Typography color="text.secondary">Rascunho · Revisão {selected.revision}</Typography>
      {stale && <Button disabled={busy} onClick={() => void open(selected)}>Recarregar rascunho</Button>}
      <Box component="fieldset" disabled={busy || stale} sx={{ border: 0, p: 0, m: 0, minWidth: 0 }}><Stack spacing={2}>
        <TrainingDraftFields accessToken={accessToken} draft={draft} onChange={setDraft} />
        <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1}>
          <Button variant="outlined" onClick={() => void submit(selected, false, draft)}>Salvar rascunho</Button>
          <Button variant="contained" onClick={() => void submit(selected, true, draft)}>Aprovar alterações</Button>
          <Button onClick={() => { setSelected(null); setDraft(null) }}>Fechar revisão</Button>
        </Stack>
      </Stack></Box>
    </Stack></CardContent></Card>}
    {busy && <LoadingState label="Processando revisão" />}
  </Stack></InstructorShell>
}
