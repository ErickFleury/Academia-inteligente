import { Box, Button, Card, CardContent, MenuItem, Stack, TextField, Typography } from '@mui/material'
import { useEffect, useRef, useState } from 'react'
import { useSearchParams } from 'react-router-dom'

import { ApiRequestError } from './clients'
import { EmptyState, LoadingState, PageHeader, StatusNotice } from './components/ui'
import { getEquipmentCatalog, type EquipmentCatalogItem } from './equipment'
import { InstructorShell } from './instructor-shell'
import { approvePendingPlan, getPendingPlan, getPendingPlans, savePendingPlan, type PendingPlan, type ReviewContent, type ReviewItem } from './training-review'

const sources = { ai: 'IA', instructor: 'Instrutor', adaptation: 'Adaptação aceita pelo cliente' }
const date = (value: string) => new Date(value).toLocaleString('pt-BR')
const emptyItem = (): ReviewItem => ({ exercise_name: '', sets: 3, repetitions: '', load_guidance: '', rest_seconds: 60, equipment_requirement: null, equipment_model_id: null })
const content = (plan: PendingPlan): ReviewContent => ({ name: plan.name, objective: plan.objective, items: plan.items.map((item) => ({ exercise_name: item.exercise_name, sets: item.sets, repetitions: item.repetitions, load_guidance: item.load_guidance, rest_seconds: item.rest_seconds, equipment_requirement: item.equipment_requirement ?? null, equipment_model_id: item.equipment_model_id ?? null })) })

export function InstructorPendingPlansPage({ accessToken, onSignOut }: { accessToken: string; onSignOut: () => void }) {
  const [searchParams] = useSearchParams()
  const requestedDraft = searchParams.get('rascunho')
  const [plans, setPlans] = useState<PendingPlan[]>([])
  const [nextOffset, setNextOffset] = useState<number | null>(null)
  const [loading, setLoading] = useState(true)
  const [selected, setSelected] = useState<PendingPlan | null>(null)
  const [draft, setDraft] = useState<ReviewContent | null>(null)
  const [models, setModels] = useState<EquipmentCatalogItem[]>([])
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
  useEffect(() => {
    let active = true
    void getEquipmentCatalog().then((items) => { if (active) setModels(items.filter((item) => item.active_quantity > 0)) }).catch(() => { if (active) setModels([]) })
    return () => { active = false }
  }, [])

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
  function changeItem(index: number, changes: Partial<ReviewItem>) {
    setDraft((value) => value && ({ ...value, items: value.items.map((item, position) => position === index ? { ...item, ...changes } : item) }))
  }
  function move(index: number, delta: number) {
    setDraft((value) => {
      if (!value) return value
      const items = [...value.items]
      ;[items[index], items[index + delta]] = [items[index + delta], items[index]]
      return { ...value, items }
    })
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
      <Typography component="h2" ref={editorHeading} tabIndex={-1} variant="h3">Revisar plano de {selected.client_name}</Typography>
      <Typography color="text.secondary">Rascunho · Revisão {selected.revision}</Typography>
      {stale && <Button disabled={busy} onClick={() => void open(selected)}>Recarregar rascunho</Button>}
      <Box component="fieldset" disabled={busy || stale} sx={{ border: 0, p: 0, m: 0, minWidth: 0 }}><Stack spacing={2}>
        <TextField required fullWidth label="Nome do plano" value={draft.name} onChange={(event) => setDraft({ ...draft, name: event.target.value })} />
        <TextField required fullWidth multiline label="Objetivo" value={draft.objective} onChange={(event) => setDraft({ ...draft, objective: event.target.value })} />
        {draft.items.map((item, index) => <Card key={index} variant="outlined"><CardContent><Stack spacing={1.5}>
          <Typography component="h3" variant="h4">Exercício {index + 1}</Typography>
          <TextField required label={`Nome do exercício ${index + 1}`} value={item.exercise_name} onChange={(event) => changeItem(index, { exercise_name: event.target.value })} />
          <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1}>
            <TextField fullWidth required label={`Séries ${index + 1}`} type="number" value={item.sets} onChange={(event) => changeItem(index, { sets: Number(event.target.value) })} />
            <TextField fullWidth required label={`Repetições ${index + 1}`} value={item.repetitions} onChange={(event) => changeItem(index, { repetitions: event.target.value })} />
          </Stack>
          <TextField required label={`Orientação de carga ${index + 1}`} value={item.load_guidance} onChange={(event) => changeItem(index, { load_guidance: event.target.value })} />
          <TextField required label={`Descanso em segundos ${index + 1}`} type="number" value={item.rest_seconds} onChange={(event) => changeItem(index, { rest_seconds: Number(event.target.value) })} />
          <TextField select label={`Equipamento do catálogo ${index + 1}`} value={item.equipment_model_id ?? ''} helperText="Unidades ativas indicam inventário do catálogo, não uso imediato." onChange={(event) => { const model = models.find((value) => value.id === event.target.value); changeItem(index, { equipment_model_id: model?.id ?? null, equipment_requirement: model?.name ?? null }) }}>
            <MenuItem value="">Sem equipamento do catálogo</MenuItem>
            {item.equipment_model_id && !models.some((model) => model.id === item.equipment_model_id) && <MenuItem disabled value={item.equipment_model_id}>{item.equipment_requirement ?? 'Referência preservada'}</MenuItem>}
            {models.map((model) => <MenuItem key={model.id} value={model.id}>{model.name} — {model.active_quantity} unidades ativas</MenuItem>)}
          </TextField>
          <Stack direction="row" sx={{ flexWrap: 'wrap', gap: 1 }}>
            <Button disabled={index === 0} aria-label={`Mover exercício ${index + 1} para cima`} onClick={() => move(index, -1)}>Subir</Button>
            <Button disabled={index === draft.items.length - 1} aria-label={`Mover exercício ${index + 1} para baixo`} onClick={() => move(index, 1)}>Descer</Button>
            <Button color="error" disabled={draft.items.length === 1} onClick={() => setDraft({ ...draft, items: draft.items.filter((_, position) => position !== index) })}>Remover exercício {index + 1}</Button>
          </Stack>
        </Stack></CardContent></Card>)}
        <Button disabled={draft.items.length >= 100} onClick={() => setDraft({ ...draft, items: [...draft.items, emptyItem()] })}>Adicionar exercício</Button>
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
