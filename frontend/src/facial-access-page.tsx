import { Box, Button, Card, CardContent, Chip, Divider, MenuItem, Stack, TextField, ToggleButton, ToggleButtonGroup, Typography } from '@mui/material'
import { useEffect, useRef, useState } from 'react'

import { biometricMessage, biometricRequest } from './biometrics'
import { ApiRequestError, listClients, type Client } from './clients'
import { AdminShell } from './components/application-shell'
import { RouterButtonLink } from './components/router-button-link'
import { LoadingState, PageHeader, StatusNotice } from './components/ui'
import { WebcamCapture } from './components/webcam-capture'
import { captureAccess, operationLabels, resultLabels, type AccessAttempt, type ClientAccessState, type CorrectionResult, type Direction, type EventPage, type PassageResult, type ProviderStatus } from './facial-access'
import { getOccupancy, type Occupancy } from './occupancy'

type Props = { accessToken: string; onSignOut: () => void; onUnauthenticated: () => void }
const dateLabel = (value: string) => new Date(value).toLocaleString('pt-BR')
const faceResult = (code: string) => resultLabels[code] ?? biometricMessage(code)

export function FacialAccessPage({ accessToken, onSignOut, onUnauthenticated }: Props) {
  const [clients, setClients] = useState<Client[]>([])
  const [clientsError, setClientsError] = useState(false)
  const [version, setVersion] = useState(0)
  const [reloadClients, setReloadClients] = useState(0)
  const expired = useRef(onUnauthenticated)
  expired.current = onUnauthenticated
  useEffect(() => {
    let active = true
    setClientsError(false)
    void listClients(accessToken).then((rows) => { if (active) setClients(rows) }).catch((error: unknown) => {
      if (!active) return
      setClientsError(true)
      if (error instanceof ApiRequestError && error.status === 401) expired.current()
    })
    return () => { active = false }
  }, [accessToken, reloadClients])
  function report(error: unknown) {
    if (error instanceof ApiRequestError && error.status === 401) expired.current()
    return biometricMessage(error)
  }
  return <AdminShell onSignOut={onSignOut}><Stack spacing={3}>
    <PageHeader eyebrow="Operação" title="Acesso facial" description="Teste entradas e saídas e acompanhe as passagens da academia." action={<RouterButtonLink to="/admin" variant="outlined">Voltar ao painel</RouterButtonLink>} />
    {clientsError && <StatusNotice severity="error">Não foi possível carregar os clientes. <Button onClick={() => setReloadClients((value) => value + 1)}>Tentar novamente</Button></StatusNotice>}
    <Box sx={{ display: 'grid', gridTemplateColumns: { xs: 'minmax(0, 1fr)', lg: 'minmax(0, 1.3fr) minmax(0, 1fr)' }, gap: 3, alignItems: 'start' }}>
      <AccessPanel token={accessToken} version={version} changed={() => setVersion((value) => value + 1)} report={report} />
      <CorrectionPanel token={accessToken} clients={clients} version={version} changed={() => setVersion((value) => value + 1)} report={report} />
    </Box>
    <EventHistory token={accessToken} clients={clients} version={version} report={report} />
  </Stack></AdminShell>
}

type PanelProps = { token: string; version: number; changed: () => void; report: (error: unknown) => string }

function AccessPanel({ token, version, changed, report }: PanelProps) {
  const [direction, setDirection] = useState<Direction>('entry')
  const [attempt, setAttempt] = useState<AccessAttempt | null>(null)
  const [camera, setCamera] = useState(false)
  const [busy, setBusy] = useState(false)
  const [uncertain, setUncertain] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [provider, setProvider] = useState<ProviderStatus | null>(null)
  const [occupancy, setOccupancy] = useState<Occupancy | null>(null)
  const [healthError, setHealthError] = useState(false)
  const [healthVersion, setHealthVersion] = useState(0)
  const [now, setNow] = useState(Date.now())
  const startCommand = useRef<string | null>(null)
  const passageCommand = useRef<{ attempt: string; command: string } | null>(null)
  const inFlight = useRef(false)
  const alive = useRef(true)
  const controller = useRef(new AbortController())
  const feedback = useRef<HTMLDivElement>(null)
  const reportRef = useRef(report)
  reportRef.current = report
  useEffect(() => {
    alive.current = true
    controller.current = new AbortController()
    const timer = window.setInterval(() => setNow(Date.now()), 1000)
    return () => { alive.current = false; controller.current.abort(); window.clearInterval(timer) }
  }, [])
  useEffect(() => {
    const abort = new AbortController()
    let checking = false
    async function health() {
      if (checking) return
      checking = true
      try {
        const status = await biometricRequest<ProviderStatus>(token, '/provider-status', undefined, abort.signal)
        if (abort.signal.aborted) return
        setProvider(status)
        if (status.available) await biometricRequest(token, '/pilot-heartbeat', { command_id: crypto.randomUUID() }, abort.signal)
        const count = await getOccupancy()
        if (!abort.signal.aborted) { setOccupancy(count); setHealthError(false) }
      } catch (reason) {
        if (!abort.signal.aborted) { setHealthError(true); reportRef.current(reason) }
      } finally { checking = false }
    }
    void health()
    const timer = window.setInterval(() => void health(), 60_000)
    return () => { abort.abort(); window.clearInterval(timer) }
  }, [token, version, healthVersion])
  useEffect(() => { if (attempt && attempt.status !== 'awaiting_capture') feedback.current?.focus() }, [attempt])
  const seconds = attempt ? Math.max(0, Math.ceil((Date.parse(attempt.expires_at) - now) / 1000)) : 0
  const authorized = attempt?.status === 'authorized' && seconds > 0 && !uncertain
  const capturable = attempt && seconds > 0 && (attempt.status === 'awaiting_capture' || attempt.can_retry) && !uncertain

  async function run(action: () => Promise<void>) {
    if (inFlight.current) return
    inFlight.current = true; setBusy(true); setError(null)
    try { await action() } catch (reason) { if (alive.current) { setError(report(reason)); setUncertain(true) } }
    finally { inFlight.current = false; if (alive.current) setBusy(false) }
  }
  async function start() {
    await run(async () => {
      startCommand.current ??= crypto.randomUUID()
      const row = await biometricRequest<AccessAttempt>(token, '/access-attempts', { direction, command_id: startCommand.current }, controller.current.signal)
      if (!alive.current) return
      startCommand.current = null; setAttempt(row); setUncertain(false); setCamera(true); changed()
    })
  }
  async function recover() {
    if (!attempt) return
    await run(async () => {
      const row = await biometricRequest<AccessAttempt>(token, `/access-attempts/${attempt.attempt_id}`, undefined, controller.current.signal)
      if (alive.current) { setAttempt(row); setUncertain(row.status === 'capturing'); changed() }
    })
  }
  async function chooseDirection(value: Direction | null) {
    if (!value || value === direction) return
    await run(async () => {
      if (attempt) await biometricRequest(token, `/access-attempts/${attempt.attempt_id}/cancel`, { command_id: crypto.randomUUID() }, controller.current.signal)
      if (alive.current) { setAttempt(null); setUncertain(false); setDirection(value); startCommand.current = null; changed() }
    })
  }
  async function capture(image: Blob) {
    if (!attempt) return
    await run(async () => {
      const row = await captureAccess(token, attempt.attempt_id, image, controller.current.signal)
      if (alive.current) { setAttempt(row); setUncertain(false); changed() }
    })
  }
  async function confirm() {
    if (!attempt) return
    await run(async () => {
      if (passageCommand.current?.attempt !== attempt.attempt_id) passageCommand.current = { attempt: attempt.attempt_id, command: crypto.randomUUID() }
      const result = await biometricRequest<PassageResult>(token, `/access-attempts/${attempt.attempt_id}/passage`, { command_id: passageCommand.current.command }, controller.current.signal)
      if (alive.current) { setAttempt({ ...attempt, status: 'confirmed', result_code: 'passage_confirmed', can_retry: false }); setOccupancy((previous) => previous ? { ...previous, occupancy: result.occupancy } : null); setUncertain(false); changed() }
    })
  }
  return <Card component="section" aria-labelledby="facial-panel-title"><CardContent><Stack spacing={2.5}>
    <Stack direction="row" sx={{ justifyContent: 'space-between', alignItems: 'center', gap: 1, flexWrap: 'wrap' }}><Typography id="facial-panel-title" component="h2" variant="h5">Teste de passagem</Typography><Chip label="Simulação" size="small" /></Stack>
    <Typography color="text.secondary">Reconheça o rosto e confirme a passagem em seguida. A catraca real não será acionada.</Typography>
    <Stack direction="row" sx={{ gap: 1, flexWrap: 'wrap', alignItems: 'center' }}>
      <Chip variant="outlined" color={provider?.available && !healthError ? 'success' : 'warning'} label={healthError ? 'Conexão indisponível' : provider ? provider.available ? 'Reconhecimento disponível' : 'Reconhecimento indisponível' : 'Verificando serviço'} />
      {occupancy && <Typography>{occupancy.occupancy} {occupancy.occupancy === 1 ? 'pessoa na academia' : 'pessoas na academia'}{occupancy.status === 'stale' ? ' · Contagem desatualizada' : ''}</Typography>}
    </Stack>
    {(healthError || provider?.available === false) && <Button onClick={() => setHealthVersion((value) => value + 1)}>Verificar serviço</Button>}
    {!!provider?.cleanup_pending && <StatusNotice severity="info">Há {provider.cleanup_pending} remoção(ões) de cadastro facial pendente(s). O sistema tentará novamente automaticamente.</StatusNotice>}
    <Box><Typography id="direction-label" gutterBottom>Sentido da passagem</Typography><ToggleButtonGroup exclusive value={direction} onChange={(_, value: Direction | null) => void chooseDirection(value)} aria-labelledby="direction-label" disabled={busy || camera} fullWidth><ToggleButton value="entry">Entrada</ToggleButton><ToggleButton value="exit">Saída</ToggleButton></ToggleButtonGroup></Box>
    <Box ref={feedback} tabIndex={-1} aria-live="polite" sx={{ outlineOffset: 4 }}>
      {error && <StatusNotice severity="error">{error}</StatusNotice>}
      {attempt && attempt.status !== 'awaiting_capture' && <Stack spacing={1}>
        {attempt.client_name && <Typography sx={{ fontWeight: 700 }}>Cliente: {attempt.client_name}</Typography>}
        <StatusNotice severity={attempt.status === 'confirmed' || authorized ? 'success' : 'info'}>{attempt.status === 'authorized' ? seconds > 0 ? 'Simulação: liberação solicitada' : 'A autorização expirou. Inicie uma nova tentativa.' : faceResult(attempt.result_code)}</StatusNotice>
        {authorized && <Typography>Confirme a passagem em até {Math.min(30, seconds)} segundos.</Typography>}
      </Stack>}
      {uncertain && <Typography sx={{ mt: 1 }}>Consulte o resultado antes de tentar outra captura.</Typography>}
    </Box>
    <Stack spacing={1}>
      {authorized && <Button variant="contained" disabled={busy} onClick={() => void confirm()}>Confirmar passagem</Button>}
      {capturable && <Button variant="contained" disabled={busy} onClick={() => setCamera(true)}>{attempt.can_retry ? 'Tentar outra captura' : 'Reconhecer rosto'}</Button>}
      {attempt && <Button disabled={busy} onClick={() => void recover()}>Consultar resultado</Button>}
      <Button variant={attempt ? 'outlined' : 'contained'} disabled={busy || !provider?.available || healthError} onClick={() => void start()}>{busy ? 'Processando...' : attempt ? 'Nova tentativa' : 'Reconhecer rosto'}</Button>
    </Stack>
    <Divider /><Typography variant="body2" color="text.secondary">Teste local sem proteção contra fotos ou vídeos: a detecção de vivacidade ainda não foi implementada.</Typography>
    <WebcamCapture open={camera} onClose={() => setCamera(false)} onCapture={capture} title={`Reconhecer rosto · ${direction === 'entry' ? 'Entrada' : 'Saída'}`} />
  </Stack></CardContent></Card>
}

function CorrectionPanel({ token, clients, version, changed, report }: PanelProps & { clients: Client[] }) {
  const [clientId, setClientId] = useState('')
  const [state, setState] = useState<ClientAccessState | null>(null)
  const [target, setTarget] = useState('outside')
  const [reason, setReason] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)
  const [reload, setReload] = useState(0)
  const command = useRef<{ fingerprint: string; id: string } | null>(null)
  const reportRef = useRef(report); reportRef.current = report
  const active = useRef(true)
  const lock = useRef(false)
  useEffect(() => { active.current = true; return () => { active.current = false } }, [])
  useEffect(() => {
    const abort = new AbortController()
    setState(null)
    if (clientId) void biometricRequest<ClientAccessState>(token, `/clients/${clientId}/state`, undefined, abort.signal).then((row) => { if (!abort.signal.aborted) setState(row) }).catch((cause: unknown) => { if (!abort.signal.aborted) setError(reportRef.current(cause)) })
    return () => abort.abort()
  }, [token, clientId, version, reload])
  async function correct() {
    if (!state || !reason.trim() || lock.current) return
    lock.current = true; setBusy(true); setError(null); setSuccess(null)
    const body = { client_id: clientId, inside: target === 'inside', expected_revision: state.revision, reason: reason.trim() }
    const fingerprint = JSON.stringify(body)
    if (command.current?.fingerprint !== fingerprint) command.current = { fingerprint, id: crypto.randomUUID() }
    try {
      const result = await biometricRequest<CorrectionResult>(token, '/state-corrections', { ...body, command_id: command.current.id })
      if (active.current) { setState(result.state); setSuccess(result.status === 'unchanged' ? 'O cliente já estava no estado escolhido. A contagem foi mantida.' : 'Presença corrigida e contagem atualizada.'); setReason(''); command.current = null; changed() }
    } catch (cause) {
      if (active.current) { setError(report(cause)); if (cause instanceof ApiRequestError && cause.status === 409) setReload((value) => value + 1) }
    } finally { lock.current = false; if (active.current) setBusy(false) }
  }
  return <Card component="section" aria-labelledby="correction-title"><CardContent><Stack component="form" spacing={2.5} onSubmit={(event) => { event.preventDefault(); void correct() }}>
    <Typography id="correction-title" component="h2" variant="h5">Corrigir presença</Typography>
    <Typography color="text.secondary">Ajuste uma entrada ou saída não registrada. O motivo ficará no histórico.</Typography>
    <TextField select fullWidth label="Cliente para correção" value={clientId} disabled={busy} onChange={(event) => { setClientId(event.target.value); setError(null); setSuccess(null); setReason('') }}><MenuItem value="">Selecione um cliente</MenuItem>{clients.map((client) => <MenuItem key={client.id} value={client.id}>{client.name}{client.client_active ? '' : ' · Inativo'}</MenuItem>)}</TextField>
    {clientId && !state && <Button disabled={busy} onClick={() => setReload((value) => value + 1)}>Consultar presença</Button>}
    {state && <Typography>Estado atual: <strong>{state.inside ? 'Dentro da academia' : 'Fora da academia'}</strong></Typography>}
    <TextField select label="Estado correto" value={target} disabled={busy || !state} onChange={(event) => setTarget(event.target.value)}><MenuItem value="inside">Dentro da academia</MenuItem><MenuItem value="outside">Fora da academia</MenuItem></TextField>
    <TextField label="Motivo da correção" value={reason} onChange={(event) => setReason(event.target.value)} multiline minRows={2} required disabled={busy || !state} slotProps={{ htmlInput: { maxLength: 1000 } }} helperText="Descreva o que aconteceu, com até 1.000 caracteres." />
    <Box aria-live="polite">{error && <StatusNotice severity="error">{error}</StatusNotice>}{success && <StatusNotice severity="success">{success}</StatusNotice>}</Box>
    <Button type="submit" variant="outlined" disabled={busy || !state || !reason.trim()}>{busy ? 'Aplicando...' : 'Aplicar correção'}</Button>
  </Stack></CardContent></Card>
}

function EventHistory({ token, clients, version, report }: Omit<PanelProps, 'changed'> & { clients: Client[] }) {
  const [clientId, setClientId] = useState('')
  const [direction, setDirection] = useState('')
  const [result, setResult] = useState('')
  const [page, setPage] = useState<EventPage>({ items: [], next_cursor: null })
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [reload, setReload] = useState(0)
  const controller = useRef<AbortController | null>(null)
  const reportRef = useRef(report); reportRef.current = report
  async function load(cursor?: string) {
    controller.current?.abort()
    const abort = new AbortController(); controller.current = abort
    setBusy(true); setError(null)
    const query = new URLSearchParams()
    if (clientId) query.set('client_id', clientId)
    if (direction) query.set('direction', direction)
    if (result) query.set('result', result)
    if (cursor) query.set('cursor', cursor)
    try {
      const next = await biometricRequest<EventPage>(token, `/events?${query}`, undefined, abort.signal)
      if (!abort.signal.aborted) setPage((previous) => ({ ...next, items: cursor ? [...previous.items, ...next.items.filter((row) => !previous.items.some((item) => item.kind === row.kind && item.id === row.id))] : next.items }))
    } catch (cause) { if (!abort.signal.aborted) setError(reportRef.current(cause)) }
    finally { if (!abort.signal.aborted) setBusy(false) }
  }
  useEffect(() => { setPage({ items: [], next_cursor: null }); void load(); return () => controller.current?.abort() }, [token, clientId, direction, result, version, reload])
  return <Card component="section" aria-labelledby="face-history-title"><CardContent><Stack spacing={2.5}>
    <Stack direction="row" sx={{ alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 1 }}><Typography component="h2" variant="h5" id="face-history-title">Eventos recentes</Typography><Button disabled={busy} onClick={() => setReload((value) => value + 1)}>Atualizar histórico</Button></Stack>
    <Stack direction={{ xs: 'column', md: 'row' }} spacing={2}>
      <TextField select fullWidth label="Filtrar por cliente" value={clientId} onChange={(event) => setClientId(event.target.value)}><MenuItem value="">Todos os clientes</MenuItem>{clients.map((client) => <MenuItem value={client.id} key={client.id}>{client.name}</MenuItem>)}</TextField>
      <TextField select fullWidth label="Filtrar por sentido" value={direction} onChange={(event) => setDirection(event.target.value)}><MenuItem value="">Todos os sentidos</MenuItem><MenuItem value="entry">Entrada</MenuItem><MenuItem value="exit">Saída</MenuItem></TextField>
      <TextField select fullWidth label="Filtrar por resultado" value={result} onChange={(event) => setResult(event.target.value)}><MenuItem value="">Todos os resultados</MenuItem>{['authorized', 'passage_confirmed', 'corrected', 'unchanged', 'unknown_face', 'client_inactive', 'already_inside', 'already_outside', 'provider_unavailable'].map((code) => <MenuItem value={code} key={code}>{faceResult(code)}</MenuItem>)}</TextField>
    </Stack>
    <Box aria-live="polite">{error && <StatusNotice severity="error">{error} <Button onClick={() => void load(page.next_cursor ?? undefined)}>Tentar novamente</Button></StatusNotice>}{busy && <LoadingState label="Carregando eventos" />}{!busy && !error && !page.items.length && <Typography color="text.secondary">Nenhum evento encontrado para estes filtros.</Typography>}</Box>
    <Stack component="ul" spacing={0} sx={{ m: 0, p: 0, listStyle: 'none' }} aria-busy={busy}>
      {page.items.map((event) => <Box component="li" key={`${event.kind}:${event.id}`} sx={{ py: 2, borderBottom: 1, borderColor: 'divider', overflowWrap: 'anywhere' }}><Stack spacing={0.75}>
        <Stack direction="row" sx={{ justifyContent: 'space-between', gap: 1, flexWrap: 'wrap' }}><Typography sx={{ fontWeight: 700 }}>{operationLabels[event.operation] ?? 'Operação facial'}{event.direction ? ` · ${event.direction === 'entry' ? 'Entrada' : 'Saída'}` : ''}</Typography><Typography component="time" dateTime={event.occurred_at} variant="body2" color="text.secondary">{dateLabel(event.occurred_at)}</Typography></Stack>
        {event.person_name && <Typography>{event.client_id ? 'Cliente' : 'Pessoa'}: {event.person_name}</Typography>}
        <Typography variant="body2">{faceResult(event.result)}</Typography>
        {event.reason && <Typography variant="body2" color="text.secondary">Motivo: {event.reason}</Typography>}
      </Stack></Box>)}
    </Stack>
    {page.next_cursor && <Button disabled={busy} onClick={() => void load(page.next_cursor!)}>Carregar mais eventos</Button>}
  </Stack></CardContent></Card>
}
