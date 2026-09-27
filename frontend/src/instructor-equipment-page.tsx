import { Button, Card, CardContent, Dialog, DialogActions, DialogContent, DialogContentText, DialogTitle, Stack, Typography } from '@mui/material'
import { useEffect, useRef, useState } from 'react'
import { ApiRequestError } from './clients'
import { EmptyState, LoadingState, PageHeader, StatusNotice } from './components/ui'
import { getInstructorEquipment, getOperationalUnits, setOperationalState, type InstructorEquipmentModel, type OperationalUnit } from './instructor-equipment'
import { InstructorShell } from './instructor-shell'
const action = (unit: OperationalUnit) => unit.operational_state === 'operational' ? 'Marcar fora de serviço' : 'Voltar a operacional'
const label = (unit: OperationalUnit) => unit.label ?? 'Unidade sem identificação'

export function InstructorEquipmentPage({ accessToken, onSignOut }: { accessToken: string; onSignOut: () => void }) {
  const [models, setModels] = useState<InstructorEquipmentModel[]>([])
  const [cursor, setCursor] = useState<string | null>(null)
  const [selected, setSelected] = useState<InstructorEquipmentModel | null>(null)
  const [units, setUnits] = useState<OperationalUnit[]>([])
  const [unitCursor, setUnitCursor] = useState<string | null>(null)
  const [confirmation, setConfirmation] = useState<OperationalUnit | null>(null)
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)
  const [stale, setStale] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const working = useRef(false)
  const heading = useRef<HTMLHeadingElement>(null)
  useEffect(() => { heading.current?.focus() }, [selected?.id])
  const failure = (reason: unknown) => setError(reason instanceof Error ? reason.message : 'Não foi possível carregar os equipamentos.')
  async function load(next?: string) { setLoading(true); setError(null); try { const page = await getInstructorEquipment(accessToken, next); setModels((old) => next ? [...old, ...page.items.filter((item) => !old.some((previous) => previous.id === item.id))] : page.items); setCursor(page.next_cursor) } catch (reason) { failure(reason) } finally { setLoading(false) } }
  useEffect(() => { void load() }, [accessToken])
  async function open(model: InstructorEquipmentModel, next?: string) {
    if (working.current) return
    working.current = true; setBusy(true); setError(null); setNotice(null)
    try { const page = await getOperationalUnits(accessToken, model.id, next); setSelected(model); setUnits((old) => next ? [...old, ...page.items.filter((item) => !old.some((previous) => previous.id === item.id))] : page.items); setUnitCursor(page.next_cursor); setStale(false) }
    catch (reason) { failure(reason) }
    finally { working.current = false; setBusy(false) }
  }
  async function toggle() {
    if (!confirmation || working.current || stale) return
    working.current = true; setBusy(true); setError(null)
    try { const unit = await setOperationalState(accessToken, confirmation); setUnits((old) => old.map((item) => item.id === unit.id ? unit : item)); setNotice('Estado operacional atualizado. A quantidade de inventário não foi alterada.') }
    catch (reason) { failure(reason); if (reason instanceof ApiRequestError && [404, 409].includes(reason.status)) setStale(true) }
    finally { setConfirmation(null); working.current = false; setBusy(false) }
  }
  return <InstructorShell onSignOut={onSignOut}><Stack spacing={3}>
    <PageHeader title="Equipamentos" eyebrow="Condição das unidades" description="Consulte as unidades e atualize seu estado operacional." />
    {error && <StatusNotice severity="error">{error}</StatusNotice>}{notice && <StatusNotice severity="success">{notice}</StatusNotice>}
    <Button disabled={loading || busy} onClick={() => { setSelected(null); void load() }}>Recarregar equipamentos</Button>
    {loading && <LoadingState label="Carregando equipamentos" />}
    {!loading && !error && !models.length && <EmptyState title="Nenhum equipamento ativo" description="Os modelos cadastrados aparecerão aqui." />}
    {models.map((model) => <Card key={model.id} component="article"><CardContent><Stack spacing={1.5}><Typography component="h2" variant="h3" sx={{ overflowWrap: 'anywhere' }}>{model.name}</Typography><Typography>{model.active_quantity} unidades ativas no inventário</Typography><Button disabled={busy} onClick={() => void open(model)}>Ver unidades</Button></Stack></CardContent></Card>)}
    {cursor && <Button disabled={busy || loading} onClick={() => void load(cursor)}>Carregar mais equipamentos</Button>}
    {busy && <LoadingState label="Processando estado operacional" />}
    {selected && <Card component="section"><CardContent><Stack spacing={2}>
      <Typography component="h2" variant="h3" ref={heading} tabIndex={-1}>Unidades de {selected.name}</Typography>
      <Button disabled={busy} onClick={() => void open(selected)}>Recarregar unidades</Button>
      {!units.length && <EmptyState title="Nenhuma unidade cadastrada" description="O cadastro de unidades é realizado pela administração." />}
      {units.map((unit) => <Card variant="outlined" key={unit.id}><CardContent><Stack spacing={1}>
        <Typography component="h3" variant="h4" sx={{ overflowWrap: 'anywhere' }}>{label(unit)}</Typography><Typography>{unit.active ? 'Ativa no inventário' : 'Inativa no inventário'}</Typography>
        <Typography>{unit.operational_state === 'operational' ? 'Operacional' : 'Fora de serviço'}</Typography>
        {unit.active && <Button variant="outlined" disabled={busy || stale} aria-label={`${action(unit)}: ${label(unit)}`} onClick={() => setConfirmation(unit)}>{action(unit)}</Button>}
      </Stack></CardContent></Card>)}
      {unitCursor && <Button disabled={busy} onClick={() => void open(selected, unitCursor)}>Carregar mais unidades</Button>}
    </Stack></CardContent></Card>}
    <Dialog open={!!confirmation} onClose={() => { if (!busy) setConfirmation(null) }} aria-labelledby="estado-operacional-titulo" aria-describedby="estado-operacional-descricao">
      <DialogTitle id="estado-operacional-titulo">{confirmation && action(confirmation)}</DialogTitle><DialogContent><DialogContentText id="estado-operacional-descricao">Confirmar a mudança de estado de {confirmation && label(confirmation)}?</DialogContentText></DialogContent>
      <DialogActions><Button autoFocus disabled={busy} onClick={() => setConfirmation(null)}>Cancelar</Button><Button disabled={busy} onClick={() => void toggle()}>Confirmar alteração</Button></DialogActions>
    </Dialog>
  </Stack></InstructorShell>
}
