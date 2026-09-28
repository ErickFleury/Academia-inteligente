import { Avatar, Box, Button, Card, CardContent, Chip, MenuItem, Stack, TextField, Typography } from '@mui/material'
import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ApiRequestError } from './clients'
import { RouterButtonLink } from './components/router-button-link'
import { EmptyState, LoadingState, PageHeader, StatusNotice } from './components/ui'
import { createManualDraft, emptyClientFilters, getInstructorClient, searchInstructorClients, type ClientFilters, type InstructorClient } from './instructor-clients'
import { InstructorShell } from './instructor-shell'
import { OnboardingForm } from './onboarding-form'
import { getResponsibleOptions } from './training-collections'
import { TrainingDraftFields } from './training-draft-fields'
import type { ReviewContent } from './training-review'

const firstDraft = (): ReviewContent => ({ name: '', objective: '', items: [{ exercise_name: '', sets: 3, repetitions: '', load_guidance: '', rest_seconds: 60, equipment_model_id: null, equipment_requirement: null }] })
const errorMessage = (error: unknown) => error instanceof Error ? error.message : 'Não foi possível carregar os clientes. Tente novamente.'
function State({ client }: { client: InstructorClient }) {
  return <Stack spacing={1}>
    <Stack direction="row" useFlexGap sx={{ flexWrap: 'wrap', gap: 0.75 }}>
      <Chip size="small" variant="outlined" color={client.onboarding_status === 'completed' ? 'success' : 'default'} label={`Onboarding: ${client.onboarding_status === 'completed' ? 'Concluído' : 'Não concluído'}`} />
      <Chip size="small" variant="outlined" color={client.draft_id ? 'warning' : client.current_id ? 'success' : 'default'} label={`Treino: ${[client.current_id && 'Plano ativo', client.draft_id && 'Pendente de aprovação'].filter(Boolean).join(' · ') || 'Sem plano'}`} />
    </Stack>
    <Typography variant="body2" color="text.secondary">Instrutor responsável: {client.responsible_instructor_name ?? 'Sem instrutor'}</Typography>
  </Stack>
}

export function InstructorClientsPage({ accessToken, onSignOut }: { accessToken: string; onSignOut: () => void }) {
  const navigate = useNavigate()
  const [filters, setFilters] = useState<ClientFilters>({ ...emptyClientFilters })
  const [applied, setApplied] = useState<ClientFilters>({ ...emptyClientFilters })
  const [items, setItems] = useState<InstructorClient[]>([])
  const [cursor, setCursor] = useState<string | null>(null)
  const [options, setOptions] = useState<{ reference: string; name: string }[]>([])
  const [optionsCursor, setOptionsCursor] = useState<string | null>(null)
  const [selected, setSelected] = useState<InstructorClient | null>(null)
  const [onboardingClient, setOnboardingClient] = useState<InstructorClient | null>(null)
  const [draft, setDraft] = useState<ReviewContent | null>(null)
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)
  const [stale, setStale] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const working = useRef(false)
  const generation = useRef(0)
  const heading = useRef<HTMLHeadingElement>(null)
  useEffect(() => { heading.current?.focus() }, [selected?.id])
  async function load(nextFilters = applied, next?: string) {
    const request = ++generation.current
    setLoading(true); setError(null)
    try { const page = await searchInstructorClients(accessToken, nextFilters, next); if (request !== generation.current) return; setItems((previous) => next ? [...previous, ...page.items.filter((item) => !previous.some((old) => old.id === item.id))] : page.items); setCursor(page.next_cursor); setApplied(nextFilters) }
    catch (reason) { if (request === generation.current) setError(errorMessage(reason)) }
    finally { if (request === generation.current) setLoading(false) }
  }
  async function loadOptions(next?: string) { try { const page = await getResponsibleOptions(accessToken, next); setOptions((old) => next ? [...old, ...page.items] : page.items); setOptionsCursor(page.next_cursor) } catch (reason) { setError(errorMessage(reason)) } }
  useEffect(() => { void load(emptyClientFilters); void loadOptions(); return () => { generation.current++ } }, [accessToken])
  async function open(id: string) {
    if (working.current) return
    working.current = true; setBusy(true); setError(null); setDraft(null)
    try { setSelected(await getInstructorClient(accessToken, id)); setStale(false) }
    catch (reason) { setError(errorMessage(reason)); setSelected(null) }
    finally { working.current = false; setBusy(false) }
  }
  async function create() {
    if (!selected || !draft || working.current || stale) return
    working.current = true; setBusy(true); setError(null)
    try { const plan = await createManualDraft(accessToken, selected.id, draft); navigate(`/instrutor/planos-pendentes?rascunho=${encodeURIComponent(plan.id)}`) }
    catch (reason) { setError(errorMessage(reason)); if (reason instanceof ApiRequestError && [404, 409].includes(reason.status)) setStale(true) }
    finally { working.current = false; setBusy(false) }
  }
  const change = (key: keyof ClientFilters, value: string) => setFilters({ ...filters, [key]: value })
  if (onboardingClient) return <OnboardingForm accessToken={accessToken} onSignOut={onSignOut} instructorClient={onboardingClient} onBack={() => { setOnboardingClient(null); void open(onboardingClient.id); void load() }} />
  return <InstructorShell onSignOut={onSignOut} contentMaxWidth="lg"><Stack spacing={3}>
    <PageHeader title="Clientes" eyebrow="Preparação de treinos" description="Encontre clientes pelo nome e acompanhe o onboarding e os planos." />
    <Stack component="form" spacing={2} sx={{ bgcolor: 'background.paper', p: { xs: 2, sm: 3 }, border: '1px solid', borderColor: 'divider', borderRadius: 3 }} onSubmit={(event) => { event.preventDefault(); setSelected(null); setDraft(null); void load(filters) }}>
      <TextField label="Nome do cliente" value={filters.search} onChange={(event) => change('search', event.target.value)} />
      <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2}>
        <TextField fullWidth select label="Onboarding" value={filters.onboarding} onChange={(event) => change('onboarding', event.target.value)}>{[['all', 'Todos'], ['completed', 'Concluído'], ['incomplete', 'Não concluído']].map(([value, label]) => <MenuItem key={value} value={value}>{label}</MenuItem>)}</TextField>
        <TextField fullWidth select label="Treino" value={filters.training} onChange={(event) => change('training', event.target.value)}>{[['all', 'Todos'], ['none', 'Sem plano'], ['pending', 'Pendente de aprovação'], ['current', 'Plano ativo']].map(([value, label]) => <MenuItem key={value} value={value}>{label}</MenuItem>)}</TextField>
        <TextField fullWidth select label="Responsabilidade" value={filters.responsibility} onChange={(event) => change('responsibility', event.target.value)}>{[['all', 'Todos'], ['none', 'Sem instrutor'], ['me', 'Eu'], ['specific', 'Instrutor específico']].map(([value, label]) => <MenuItem key={value} value={value}>{label}</MenuItem>)}</TextField>
      </Stack>
      {filters.responsibility === 'specific' && <><TextField required select label="Instrutor específico" value={filters.responsible} onChange={(event) => change('responsible', event.target.value)}>{options.map((option) => <MenuItem key={option.reference} value={option.reference}>{option.name}</MenuItem>)}</TextField>{optionsCursor && <Button onClick={() => void loadOptions(optionsCursor)}>Carregar mais instrutores</Button>}</>}
      <Button type="submit" variant="contained" sx={{ alignSelf: { sm: 'flex-start' } }} disabled={loading || busy}>Pesquisar clientes</Button>
    </Stack>
    {error && <StatusNotice severity="error">{error}</StatusNotice>}
    <Box sx={{ display: 'grid', gridTemplateColumns: { xs: 'minmax(0, 1fr)', lg: 'minmax(300px, 0.9fr) minmax(0, 1.3fr)' }, gap: 3, alignItems: 'start' }}>
    <Stack component="section" aria-label="Lista de clientes" spacing={2} sx={{ minWidth: 0 }}>
    <Stack direction="row" sx={{ flexWrap: 'wrap', alignItems: 'center', justifyContent: 'space-between', gap: 1 }}>
      <Typography component="h2" variant="h3">Clientes encontrados</Typography>
      <Button disabled={loading || busy} onClick={() => void load()}>Recarregar lista</Button>
    </Stack>
    {loading && <LoadingState label="Carregando clientes" />}
    {!loading && !error && !items.length && <EmptyState title="Nenhum cliente encontrado" description="Ajuste o nome ou os filtros e tente novamente." />}
    {items.map((client) => <Card key={client.id} component="article" sx={{ borderColor: selected?.id === client.id ? 'primary.main' : 'divider' }}><CardContent><Stack spacing={2}>
      <Stack direction="row" spacing={1.5} sx={{ alignItems: 'center' }}>
        <Avatar aria-hidden="true" sx={{ bgcolor: 'rgba(255,133,100,0.10)', color: 'primary.main' }}>{client.name.slice(0, 1)}</Avatar>
        <Typography component="h3" variant="h3" sx={{ overflowWrap: 'anywhere', minWidth: 0 }}>{client.name}</Typography>
      </Stack>
      <State client={client} />
      <Button disabled={busy} variant="outlined" sx={{ alignSelf: 'flex-start' }} onClick={() => void open(client.id)}>Abrir cliente</Button>
    </Stack></CardContent></Card>)}
    {cursor && <Button disabled={loading || busy} onClick={() => void load(applied, cursor)}>Carregar mais clientes</Button>}
    </Stack>
    <Stack spacing={2} sx={{ minWidth: 0, position: { lg: 'sticky' }, top: 24 }}>
    {!selected && !busy && <Box sx={{ display: { xs: 'none', lg: 'block' } }}><EmptyState title="Selecione um cliente" description="Consulte o onboarding e acesse os treinos no espaço ao lado da lista." /></Box>}
    {busy && <LoadingState label="Processando dados de treino" />}
    {selected && <Card component="section" sx={{ borderTop: '3px solid', borderTopColor: 'primary.main' }}><CardContent><Stack spacing={2}>
      <Typography component="h2" tabIndex={-1} ref={heading} variant="h3" sx={{ scrollMarginTop: 88, overflowWrap: 'anywhere' }}>Treinos de {selected.name}</Typography><State client={selected} />
      <Button disabled={busy} onClick={() => setOnboardingClient(selected)}>{selected.onboarding_status === 'completed' ? 'Editar onboarding concluído' : 'Preencher ou continuar onboarding'}</Button>
      <Button disabled={busy} onClick={() => void open(selected.id)}>Recarregar cadastro</Button>
      {selected.draft_id && <RouterButtonLink to={`/instrutor/planos-pendentes?rascunho=${selected.draft_id}`}>Abrir rascunho</RouterButtonLink>}
      {selected.current_id && <RouterButtonLink to={`/instrutor/todos-os-planos?plano=${selected.current_id}`}>Ver plano atual e histórico</RouterButtonLink>}
      {!selected.current_id && !selected.draft_id && !draft && <Button variant="contained" disabled={busy || stale} onClick={() => setDraft(firstDraft())}>Criar primeiro rascunho</Button>}
      {draft && <Box component="form" onSubmit={(event) => { event.preventDefault(); void create() }}><Stack component="fieldset" disabled={busy || stale} spacing={2} sx={{ border: 0, p: 0, m: 0, minWidth: 0 }}><Typography>O rascunho será salvo para revisão. A aprovação é uma ação separada.</Typography><TrainingDraftFields accessToken={accessToken} draft={draft} onChange={setDraft} /><Button type="submit" variant="contained">Salvar primeiro rascunho</Button><Button onClick={() => setDraft(null)}>Cancelar criação</Button></Stack></Box>}
    </Stack></CardContent></Card>}
    </Stack>
    </Box>
  </Stack></InstructorShell>
}
