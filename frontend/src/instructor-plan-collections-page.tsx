import { Box, Button, Card, CardContent, Dialog, DialogActions, DialogContent, DialogContentText, DialogTitle, MenuItem, Stack, TextField, Typography } from '@mui/material'
import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'

import { ApiRequestError } from './clients'
import { EmptyState, LoadingState, PageHeader, StatusNotice } from './components/ui'
import { InstructorShell } from './instructor-shell'
import { cloneCurrentPlan, emptyFilters, ExistingDraftError, getApprovedPlan, getPlanCollection, getPlanHistory, getResponsibleOptions, type ApprovedDetail, type ApprovedPlan, type DraftConflict, type PlanFilters } from './training-collections'

const approvalDate = (value: string) => new Date(value).toLocaleString('pt-BR', { timeZone: 'America/Sao_Paulo' })
const message = (error: unknown) => error instanceof Error ? error.message : 'Não foi possível carregar os planos. Tente novamente.'

export function InstructorPlanCollectionsPage({ accessToken, onSignOut, mine = false }: { accessToken: string; onSignOut: () => void; mine?: boolean }) {
  const navigate = useNavigate()
  const [filters, setFilters] = useState<PlanFilters>({ ...emptyFilters })
  const [applied, setApplied] = useState<PlanFilters>({ ...emptyFilters })
  const [plans, setPlans] = useState<ApprovedPlan[]>([])
  const [cursor, setCursor] = useState<string | null>(null)
  const [options, setOptions] = useState<{ reference: string; name: string }[]>([])
  const [optionsCursor, setOptionsCursor] = useState<string | null>(null)
  const [detail, setDetail] = useState<ApprovedDetail | null>(null)
  const [history, setHistory] = useState<ApprovedPlan[]>([])
  const [historyCursor, setHistoryCursor] = useState<string | null>(null)
  const [historyAnchor, setHistoryAnchor] = useState<string | null>(null)
  const [conflict, setConflict] = useState<DraftConflict | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [stale, setStale] = useState(false)
  const [loading, setLoading] = useState(true)
  const working = useRef(false)
  const heading = useRef<HTMLHeadingElement>(null)
  const generation = useRef(0)
  useEffect(() => { heading.current?.focus() }, [detail?.id])

  async function load(selectedFilters = applied, next?: string) {
    const request = ++generation.current
    setLoading(true); setError(null)
    try {
      const page = await getPlanCollection(accessToken, mine, selectedFilters, next)
      if (request !== generation.current) return
      setPlans((previous) => next ? [...previous, ...page.items.filter((item) => !previous.some((old) => old.id === item.id))] : page.items)
      setCursor(page.next_cursor); setApplied(selectedFilters)
    } catch (reason) { if (request === generation.current) setError(message(reason)) }
    finally { if (request === generation.current) setLoading(false) }
  }
  async function loadOptions(next?: string) {
    try {
      const page = await getResponsibleOptions(accessToken, next)
      setOptions((previous) => next ? [...previous, ...page.items] : page.items); setOptionsCursor(page.next_cursor)
    } catch (reason) { setError(message(reason)) }
  }
  useEffect(() => { void load(emptyFilters); void loadOptions(); return () => { generation.current++ } }, [accessToken, mine])
  async function open(id: string, historical = false) {
    if (working.current) return
    working.current = true; setBusy(true); setError(null)
    try {
      const selected = await getApprovedPlan(accessToken, id)
      if (!historical) {
        const page = await getPlanHistory(accessToken, id)
        setHistory(page.items); setHistoryCursor(page.next_cursor); setHistoryAnchor(id)
      }
      setDetail(selected); setConflict(null); setStale(false)
    } catch (reason) { setError(message(reason)) }
    finally { working.current = false; setBusy(false) }
  }
  async function moreHistory() {
    if (!historyAnchor || !historyCursor || working.current) return
    working.current = true; setBusy(true)
    try {
      const page = await getPlanHistory(accessToken, historyAnchor, historyCursor)
      setHistory((previous) => [...previous, ...page.items.filter((item) => !previous.some((old) => old.id === item.id))]); setHistoryCursor(page.next_cursor)
    } catch (reason) { setError(message(reason)) }
    finally { working.current = false; setBusy(false) }
  }
  async function edit(discard?: DraftConflict) {
    if (!detail || working.current || stale) return
    working.current = true; setBusy(true); setError(null)
    try {
      const draft = await cloneCurrentPlan(accessToken, detail, discard)
      navigate(`/instrutor/planos-pendentes?rascunho=${encodeURIComponent(draft.id)}`)
    } catch (reason) {
      if (reason instanceof ExistingDraftError) setConflict(reason.draft)
      else { setConflict(null); setError(message(reason)); if (reason instanceof ApiRequestError && [404, 409].includes(reason.status)) setStale(true) }
    } finally { working.current = false; setBusy(false) }
  }
  return <InstructorShell onSignOut={onSignOut}><Stack spacing={3}>
    <PageHeader eyebrow="Treinos aprovados" title={mine ? 'Meus planos' : 'Todos os planos'} description={mine ? 'Planos atuais sob sua responsabilidade.' : 'Consulte os treinos atuais e seu histórico de aprovação.'} />
    {!mine && <Box component="form" onSubmit={(event) => { event.preventDefault(); setDetail(null); void load(filters) }}><Stack spacing={2}>
      <TextField label="Nome do cliente" value={filters.search} onChange={(event) => setFilters({ ...filters, search: event.target.value })} />
      <TextField select label="Instrutor responsável" value={filters.responsible} onChange={(event) => setFilters({ ...filters, responsible: event.target.value })}><MenuItem value="">Todos</MenuItem>{options.map((option) => <MenuItem key={option.reference} value={option.reference}>{option.name}</MenuItem>)}</TextField>
      {optionsCursor && <Button onClick={() => void loadOptions(optionsCursor)}>Carregar mais instrutores</Button>}
      <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2}>
        <TextField fullWidth type="date" label="Aprovação a partir de" slotProps={{ inputLabel: { shrink: true } }} value={filters.start} onChange={(event) => setFilters({ ...filters, start: event.target.value })} />
        <TextField fullWidth type="date" label="Aprovação até" slotProps={{ inputLabel: { shrink: true } }} value={filters.end} onChange={(event) => setFilters({ ...filters, end: event.target.value })} />
      </Stack>
      <Typography variant="body2">Datas no horário de São Paulo, incluindo os dias selecionados. Para um único dia, preencha a mesma data nos dois campos.</Typography>
      <Button type="submit" variant="contained" disabled={loading || busy}>Aplicar filtros</Button>
    </Stack></Box>}
    {error && <StatusNotice severity="error">{error}</StatusNotice>}
    <Box><Button disabled={busy || loading} onClick={() => { setDetail(null); void load() }}>Recarregar planos</Button></Box>
    {loading && <LoadingState label="Carregando planos" />}
    {!loading && !error && !plans.length && <EmptyState title="Nenhum plano encontrado" description="Não há planos atuais para esta consulta." />}
    {plans.map((plan) => <Card component="article" key={plan.id}><CardContent><Stack spacing={1}>
      <Typography component="h2" variant="h3" sx={{ overflowWrap: 'anywhere' }}>{plan.client_name}</Typography>
      <Typography sx={{ overflowWrap: 'anywhere' }}>{plan.name}</Typography>
      <Typography>Instrutor responsável: {plan.responsible_instructor_name ?? 'Não informado'}</Typography>
      <Typography>Aprovado em {approvalDate(plan.approved_at)} · Atual</Typography>
      <Button disabled={busy} onClick={() => void open(plan.id)}>Ver plano e histórico</Button>
    </Stack></CardContent></Card>)}
    {cursor && <Button disabled={loading || busy} onClick={() => void load(applied, cursor)}>Carregar mais planos</Button>}
    {busy && <LoadingState label="Carregando detalhes do plano" />}
    {detail && <Card component="section"><CardContent><Stack spacing={2}>
      <Typography ref={heading} tabIndex={-1} component="h2" variant="h3">{detail.name} — {detail.client_name}</Typography>
      <Typography>{detail.status === 'current' ? 'Plano atual' : 'Histórico — somente leitura'}</Typography>
      <Typography>Instrutor responsável: {detail.responsible_instructor_name ?? 'Não informado'} · {approvalDate(detail.approved_at)}</Typography>
      <Typography sx={{ overflowWrap: 'anywhere' }}>{detail.objective}</Typography>
      {detail.items.map((item, index) => <Box key={index} sx={{ overflowWrap: 'anywhere' }}><Typography component="h3" variant="h4">{index + 1}. {item.exercise_name}</Typography><Typography>{item.sets} séries · {item.repetitions} repetições · {item.rest_seconds}s de descanso</Typography><Typography>{item.load_guidance}</Typography>{item.equipment_requirement && <Typography>Equipamento registrado: {item.equipment_requirement}</Typography>}</Box>)}
      {detail.status === 'current' && <Button variant="contained" disabled={busy || stale} onClick={() => void edit()}>Editar</Button>}
      {stale && <Button disabled={busy} onClick={() => void open(detail.id)}>Recarregar detalhes</Button>}
      <Typography component="h3" variant="h4">Histórico de aprovações</Typography>
      {history.map((item) => <Button key={item.id} disabled={busy} onClick={() => void open(item.id, true)}>{item.name} · {approvalDate(item.approved_at)} · {item.responsible_instructor_name ?? 'Não informado'}{item.status === 'current' ? ' · Atual' : ''}</Button>)}
      {historyCursor && <Button disabled={busy} onClick={() => void moreHistory()}>Carregar mais histórico</Button>}
    </Stack></CardContent></Card>}
    <Dialog open={conflict !== null} onClose={() => { if (!busy) setConflict(null) }} aria-labelledby="confirmar-substituicao-titulo" aria-describedby="confirmar-substituicao-descricao">
      <DialogTitle id="confirmar-substituicao-titulo">Substituir rascunho existente?</DialogTitle>
      <DialogContent><DialogContentText id="confirmar-substituicao-descricao">O rascunho “{conflict?.name}” (revisão {conflict?.revision}) será descartado. Um novo rascunho será copiado do plano atual. O treino atual só muda após uma nova aprovação.</DialogContentText></DialogContent>
      <DialogActions><Button autoFocus disabled={busy} onClick={() => setConflict(null)}>Cancelar</Button><Button color="error" disabled={busy} onClick={() => { if (conflict) void edit(conflict) }}>Descartar e criar rascunho</Button></DialogActions>
    </Dialog>
  </Stack></InstructorShell>
}
