import { Box, Button, Card, CardContent, Chip, Collapse, Divider, Dialog, DialogActions, DialogContent, DialogContentText, DialogTitle, MenuItem, Stack, Tab, Tabs, TextField, Typography } from '@mui/material'
import { useEffect, useRef, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'

import { ApiRequestError } from './clients'
import { EmptyState, LoadingState, PageHeader, StatusNotice } from './components/ui'
import { TrainingPlanContent } from './components/training-plan-content'
import { InstructorShell } from './instructor-shell'
import { cloneCurrentPlan, emptyFilters, ExistingDraftError, getApprovedPlan, getPlanCollection, getPlanHistory, getResponsibleOptions, type ApprovedDetail, type ApprovedPlan, type DraftConflict, type PlanFilters } from './training-collections'

const approvalDate = (value: string) => new Date(value).toLocaleString('pt-BR', { timeZone: 'America/Sao_Paulo', dateStyle: 'medium', timeStyle: 'short' })
const shortDate = (value: string) => new Date(value).toLocaleDateString('pt-BR', { timeZone: 'America/Sao_Paulo', dateStyle: 'medium' })
const message = (error: unknown) => error instanceof Error ? error.message : 'Não foi possível carregar os planos. Tente novamente.'

export function InstructorPlanCollectionsPage({ accessToken, onSignOut, mine = false }: { accessToken: string; onSignOut: () => void; mine?: boolean }) {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const requestedPlan = searchParams.get('plano')
  const [showFilters, setShowFilters] = useState(false)
  const [tab, setTab] = useState<'plan' | 'history'>('plan')
  const listButtons = useRef(new Map<string, HTMLButtonElement>())
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
  const detailSection = useRef<HTMLElement>(null)
  const generation = useRef(0)
  useEffect(() => {
    heading.current?.focus({ preventScroll: true })
    detailSection.current?.scrollIntoView?.({ block: 'start' })
  }, [detail?.id])

  function closeDetail() {
    setDetail(null)
    requestAnimationFrame(() => { if (historyAnchor) listButtons.current.get(historyAnchor)?.focus() })
  }

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
  useEffect(() => {
    setFilters({ ...emptyFilters }); setDetail(null); setHistoryAnchor(null); setShowFilters(false)
    void load(emptyFilters)
    if (!mine) void loadOptions()
    return () => { generation.current++ }
  }, [accessToken, mine])
  useEffect(() => { if (requestedPlan) void open(requestedPlan) }, [accessToken, requestedPlan])
  async function open(id: string, historical = false) {
    if (working.current) return
    working.current = true; setBusy(true); setError(null)
    try {
      const selected = await getApprovedPlan(accessToken, id)
      if (!historical) {
        const page = await getPlanHistory(accessToken, id)
        setHistory(page.items); setHistoryCursor(page.next_cursor); setHistoryAnchor(id)
      }
      setDetail(selected); setTab('plan'); setConflict(null); setStale(false)
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
  const hasFilters = Object.values(applied).some((value) => value.trim())
  return <InstructorShell onSignOut={onSignOut} contentMaxWidth="lg"><Stack spacing={3}>
    <PageHeader eyebrow="Treinos aprovados" title={mine ? 'Meus planos' : 'Todos os planos'}
      description={mine ? 'Acompanhe os treinos sob sua responsabilidade e consulte cada aprovação.' : 'Encontre um cliente, confira o treino atual e acompanhe as versões aprovadas.'} />
    {!mine && <Card component="form" onSubmit={(event) => { event.preventDefault(); setDetail(null); void load(filters) }} sx={{ display: { xs: detail ? 'none' : 'block', lg: 'block' } }}>
      <CardContent><Stack spacing={2}>
        <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1.5}>
          <TextField fullWidth label="Nome do cliente" placeholder="Encontre um treino pelo cliente" value={filters.search} onChange={(event) => setFilters({ ...filters, search: event.target.value })} />
          <Button type="submit" variant="contained" disabled={loading || busy} sx={{ flexShrink: 0 }}>Aplicar filtros</Button>
        </Stack>
        <Stack direction="row" sx={{ flexWrap: 'wrap', gap: 1, alignItems: 'center' }}>
          <Button aria-expanded={showFilters} aria-controls="filtros-avancados-planos" onClick={() => setShowFilters(!showFilters)}>{showFilters ? 'Menos filtros' : 'Mais filtros'}</Button>
          {(hasFilters || Object.values(filters).some(Boolean)) && <Button disabled={loading || busy} onClick={() => { setFilters({ ...emptyFilters }); setDetail(null); void load(emptyFilters) }}>Limpar filtros</Button>}
          {hasFilters && <Chip size="small" label="Consulta filtrada" />}
        </Stack>
        <Collapse in={showFilters} id="filtros-avancados-planos">
          <Stack spacing={2}>
            <TextField select fullWidth label="Instrutor responsável" value={filters.responsible} onChange={(event) => setFilters({ ...filters, responsible: event.target.value })}>
              <MenuItem value="">Todos</MenuItem>{options.map((option) => <MenuItem key={option.reference} value={option.reference}>{option.name}</MenuItem>)}
            </TextField>
            {optionsCursor && <Button onClick={() => void loadOptions(optionsCursor)}>Carregar mais instrutores</Button>}
            <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2}>
              <TextField fullWidth type="date" label="Aprovação a partir de" slotProps={{ inputLabel: { shrink: true } }} value={filters.start} onChange={(event) => setFilters({ ...filters, start: event.target.value })} />
              <TextField fullWidth type="date" label="Aprovação até" slotProps={{ inputLabel: { shrink: true } }} value={filters.end} onChange={(event) => setFilters({ ...filters, end: event.target.value })} />
            </Stack>
            <Typography variant="body2" color="text.secondary">Datas no horário de São Paulo, incluindo os dias selecionados. Para um único dia, preencha a mesma data nos dois campos.</Typography>
          </Stack>
        </Collapse>
      </Stack></CardContent>
    </Card>}
    {error && <StatusNotice severity="error">{error}</StatusNotice>}
    <Box sx={{ display: 'grid', gridTemplateColumns: { xs: 'minmax(0, 1fr)', lg: 'minmax(260px, 0.8fr) minmax(0, 1.8fr)' }, gap: 3, alignItems: 'start' }}>
      <Stack component="section" aria-label="Lista de planos atuais" spacing={2} sx={{ minWidth: 0, display: { xs: detail ? 'none' : 'flex', lg: 'flex' }, position: { lg: 'sticky' }, top: 24 }}>
        <Stack direction="row" sx={{ alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 1 }}>
          <Typography component="h2" variant="h3">Planos atuais</Typography>
          <Button disabled={busy || loading} onClick={() => { setDetail(null); void load() }}>Recarregar planos</Button>
        </Stack>
        <Typography variant="body2" color="text.secondary" aria-live="polite">{plans.length} {plans.length === 1 ? 'plano carregado' : 'planos carregados'}{cursor ? ' · Há mais resultados' : ''}</Typography>
        {loading && <LoadingState label="Carregando planos" />}
        {!loading && !error && !plans.length && <EmptyState title="Nenhum plano encontrado" description={mine ? 'Os planos que você aprovar aparecerão aqui enquanto estiverem sob sua responsabilidade.' : 'Tente outro nome ou ajuste os filtros da consulta.'} />}
        <Stack spacing={1.5} sx={(theme) => ({ maxHeight: { lg: '70vh' }, overflowY: { lg: 'auto' }, scrollbarWidth: 'thin', scrollbarColor: `${theme.palette.divider} transparent`, p: 0.5 })}>
          {plans.map((plan) => <Button key={plan.id} ref={(element) => { if (element) listButtons.current.set(plan.id, element); else listButtons.current.delete(plan.id) }}
            aria-label={`Ver plano e histórico de ${plan.client_name}`} aria-pressed={Boolean(detail && historyAnchor === plan.id)}
            disabled={busy} onClick={() => void open(plan.id)} color="inherit"
            sx={{ display: 'block', flexShrink: 0, textAlign: 'left', p: 2, border: '1px solid', borderColor: detail && historyAnchor === plan.id ? 'primary.main' : 'divider', bgcolor: detail && historyAnchor === plan.id ? 'action.selected' : 'background.paper', width: '100%' }}>
            <Stack spacing={1}>
              <Stack direction="row" sx={{ justifyContent: 'space-between', alignItems: 'start', gap: 1 }}>
                <Typography component="span" sx={{ fontWeight: 800, overflowWrap: 'anywhere' }}>{plan.name}</Typography>
                <Chip component="span" size="small" color="success" variant="outlined" label="Atual" />
              </Stack>
              <Typography component="span" variant="body2" sx={{ fontWeight: 700, overflowWrap: 'anywhere' }}>Cliente: {plan.client_name}</Typography>
              <Typography component="span" variant="caption" color="text.secondary" sx={{ overflowWrap: 'anywhere' }}>Responsável: {plan.responsible_instructor_name ?? 'Não informado'}</Typography>
              <Typography component="span" variant="caption" color="text.secondary">Aprovado em {shortDate(plan.approved_at)}</Typography>
              <Typography component="span" variant="body2" color="primary.main" sx={{ fontWeight: 750 }}>Ver plano e histórico →</Typography>
            </Stack>
          </Button>)}
        </Stack>
        {cursor && <Button disabled={loading || busy} onClick={() => void load(applied, cursor)}>Carregar mais planos</Button>}
      </Stack>
      <Box sx={{ minWidth: 0, display: { xs: detail || busy ? 'block' : 'none', lg: 'block' } }}>
        {busy && <LoadingState label="Carregando detalhes do plano" />}
        {!detail && !busy && <Card variant="outlined"><CardContent sx={{ py: 7 }}><Stack spacing={1.5} sx={{ maxWidth: 380, mx: 'auto' }}>
          <Typography variant="overline" color="primary.main">Visão do treino</Typography>
          <Typography component="h2" variant="h3">Selecione um plano para consultar</Typography>
          <Typography color="text.secondary">Veja a sequência de exercícios, as orientações de carga e o histórico de aprovações em um só lugar.</Typography>
        </Stack></CardContent></Card>}
        {detail && <Card component="section" ref={detailSection} aria-label="Detalhes do plano" sx={{ scrollMarginTop: { xs: 80, md: 24 } }}><CardContent sx={{ p: { xs: 2, sm: 3 } }}><Stack spacing={3}>
          <Box><Button disabled={busy} onClick={closeDetail}>← Voltar à lista</Button></Box>
          <Stack spacing={1.5}>
            <Stack direction="row" sx={{ flexWrap: 'wrap', gap: 1 }}>
              <Chip color={detail.status === 'current' ? 'success' : 'default'} size="small" label={detail.status === 'current' ? 'Plano atual' : 'Histórico — somente leitura'} />
              <Chip size="small" variant="outlined" label="Aprovado" />
            </Stack>
            <Typography ref={heading} tabIndex={-1} component="h2" variant="h3" sx={{ fontSize: { xs: '1.35rem', sm: '1.6rem' }, overflowWrap: 'anywhere', scrollMarginTop: { xs: 88, md: 24 } }}>{detail.name}</Typography>
            <Typography sx={{ fontWeight: 700, overflowWrap: 'anywhere' }}>Cliente: {detail.client_name}</Typography>
            <Box component="dl" sx={{ m: 0, display: 'grid', gridTemplateColumns: { xs: '1fr', sm: '1fr 1fr' }, gap: 2 }}>
              <Box><Typography component="dt" variant="caption" color="text.secondary">Instrutor responsável</Typography><Typography component="dd" sx={{ m: 0, overflowWrap: 'anywhere' }}>{detail.responsible_instructor_name ?? 'Não informado'}</Typography></Box>
              <Box><Typography component="dt" variant="caption" color="text.secondary">Aprovado em</Typography><Typography component="dd" sx={{ m: 0 }}>{approvalDate(detail.approved_at)}</Typography></Box>
            </Box>
            {detail.status === 'current' ? <Stack spacing={1}>
              <Box><Button variant="outlined" disabled={busy || stale} onClick={() => void edit()}>Editar</Button></Box>
              <Typography variant="caption" color="text.secondary">A edição abre um rascunho. Este treino permanece atual até uma nova aprovação.</Typography>
            </Stack> : historyAnchor && <Box><Button disabled={busy} onClick={() => void open(historyAnchor)}>Voltar ao plano atual</Button></Box>}
            {stale && <Button disabled={busy} onClick={() => void open(detail.id)}>Recarregar detalhes</Button>}
          </Stack>
          <Divider />
          <Tabs value={tab} onChange={(_, value: 'plan' | 'history') => setTab(value)} aria-label="Conteúdo do plano" variant="fullWidth">
            <Tab id="aba-treino" aria-controls="painel-treino" value="plan" label="Treino" />
            <Tab id="aba-historico" aria-controls="painel-historico" value="history" label="Histórico" />
          </Tabs>
          <Box role="tabpanel" id="painel-treino" aria-labelledby="aba-treino" hidden={tab !== 'plan'}>{tab === 'plan' && <TrainingPlanContent plan={detail} />}</Box>
          <Box role="tabpanel" id="painel-historico" aria-labelledby="aba-historico" hidden={tab !== 'history'}>
            {tab === 'history' && <Stack spacing={2}>
              <Typography component="h3" variant="h3">Histórico de aprovações</Typography>
              <Typography variant="body2" color="text.secondary">Consulte cada versão com a data e o responsável pela aprovação. Versões anteriores são somente leitura.</Typography>
              {history.map((item) => <Button key={item.id} disabled={busy} onClick={() => void open(item.id, true)} color="inherit" variant="outlined" sx={{ textAlign: 'left', justifyContent: 'flex-start', p: 2 }}>
                <Stack spacing={0.75} sx={{ minWidth: 0 }}>
                  <Typography component="span" sx={{ fontWeight: 750, overflowWrap: 'anywhere' }}>{item.name}{item.status === 'current' ? ' · Atual' : ''}</Typography>
                  <Typography component="span" variant="body2" sx={{ overflowWrap: 'anywhere' }}>Cliente: {item.client_name}</Typography>
                  <Typography component="span" variant="body2">{approvalDate(item.approved_at)}</Typography>
                  <Typography component="span" variant="body2" color="text.secondary" sx={{ overflowWrap: 'anywhere' }}>{item.responsible_instructor_name ?? 'Não informado'}</Typography>
                </Stack>
              </Button>)}
              {historyCursor && <Button disabled={busy} onClick={() => void moreHistory()}>Carregar mais histórico</Button>}
            </Stack>}
          </Box>
        </Stack></CardContent></Card>}
      </Box>
    </Box>
    <Dialog open={conflict !== null} onClose={() => { if (!busy) setConflict(null) }} aria-labelledby="confirmar-substituicao-titulo" aria-describedby="confirmar-substituicao-descricao">
      <DialogTitle id="confirmar-substituicao-titulo">Substituir rascunho existente?</DialogTitle>
      <DialogContent><DialogContentText id="confirmar-substituicao-descricao">O rascunho “{conflict?.name}” (revisão {conflict?.revision}) será descartado. Um novo rascunho será copiado do plano atual. O treino atual só muda após uma nova aprovação.</DialogContentText></DialogContent>
      <DialogActions><Button autoFocus disabled={busy} onClick={() => setConflict(null)}>Cancelar</Button><Button color="error" disabled={busy} onClick={() => { if (conflict) void edit(conflict) }}>Descartar e criar rascunho</Button></DialogActions>
    </Dialog>
  </Stack></InstructorShell>
}
