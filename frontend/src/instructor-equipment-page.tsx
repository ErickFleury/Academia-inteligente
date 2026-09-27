import { Box, Button, Card, Chip, Dialog, DialogActions, DialogContent, DialogContentText, DialogTitle, Divider, LinearProgress, Stack, TextField, Typography } from '@mui/material'
import { useEffect, useRef, useState } from 'react'
import { ApiRequestError } from './clients'
import { EquipmentGlyph, InventoryChip, OperationalChip } from './components/equipment-presentation'
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
  const [search, setSearch] = useState('')
  const [query, setQuery] = useState('')
  const working = useRef(false)
  const listWorking = useRef(false)
  const generation = useRef(0)
  const heading = useRef<HTMLHeadingElement>(null)
  const selectionButtons = useRef(new Map<string, HTMLButtonElement>())
  useEffect(() => { heading.current?.focus() }, [selected?.id])
  const failure = (reason: unknown) => setError(reason instanceof Error ? reason.message : 'Não foi possível carregar os equipamentos.')
  async function load(next?: string, term = query) {
    if (listWorking.current) return
    listWorking.current = true
    const current = generation.current
    setLoading(true); setError(null)
    try {
      const page = await getInstructorEquipment(accessToken, next, term)
      if (current !== generation.current) return
      setModels((old) => next ? [...old, ...page.items.filter((item) => !old.some((previous) => previous.id === item.id))] : page.items)
      setCursor(page.next_cursor); setQuery(term)
    } catch (reason) { if (current === generation.current) failure(reason) }
    finally { if (current === generation.current) { listWorking.current = false; setLoading(false) } }
  }
  useEffect(() => { listWorking.current = false; working.current = false; setSelected(null); void load(undefined, ''); return () => { generation.current++ } }, [accessToken])
  async function open(model: InstructorEquipmentModel, next?: string) {
    if (working.current) return
    working.current = true; setBusy(true); setError(null); setNotice(null)
    const current = generation.current
    try {
      const page = await getOperationalUnits(accessToken, model.id, next)
      if (current !== generation.current) return
      setSelected(model)
      setUnits((old) => next ? [...old, ...page.items.filter((item) => !old.some((previous) => previous.id === item.id))] : page.items)
      setUnitCursor(page.next_cursor); setStale(false)
    } catch (reason) { if (current === generation.current) failure(reason) }
    finally { if (current === generation.current) { working.current = false; setBusy(false) } }
  }
  function back() { const id = selected?.id; setSelected(null); setNotice(null); setTimeout(() => { if (id) selectionButtons.current.get(id)?.focus() }, 0) }
  async function toggle() {
    if (!confirmation || working.current || stale) return
    working.current = true; setBusy(true); setError(null)
    try {
      const unit = await setOperationalState(accessToken, confirmation)
      setUnits((old) => old.map((item) => item.id === unit.id ? unit : item))
      setNotice('Estado operacional atualizado. A quantidade de inventário não foi alterada.')
    } catch (reason) { failure(reason); if (reason instanceof ApiRequestError && [404, 409].includes(reason.status)) setStale(true) }
    finally { setConfirmation(null); working.current = false; setBusy(false) }
  }
  return <InstructorShell onSignOut={onSignOut} contentMaxWidth="lg"><Stack spacing={3} sx={{ minWidth: 0 }}>
    <PageHeader title="Equipamentos" eyebrow="Rotina da academia" description="Consulte os equipamentos e acompanhe a condição de cada unidade." action={<Button disabled={loading || busy} onClick={() => { setSelected(null); void load() }}>Recarregar equipamentos</Button>} />
    {error && <StatusNotice severity="error">{error}</StatusNotice>}{notice && <StatusNotice severity="success">{notice}</StatusNotice>}
    <Box sx={{ display: 'grid', gridTemplateColumns: { xs: 'minmax(0, 1fr)', lg: '300px minmax(0, 1fr)' }, alignItems: 'start', gap: 3 }}>
      <Card sx={{ display: { xs: selected ? 'none' : 'block', lg: 'block' }, overflow: 'hidden' }}>
        <Box component="form" sx={{ p: 2, borderBottom: '1px solid', borderColor: 'divider' }} onSubmit={(event) => { event.preventDefault(); setSelected(null); void load(undefined, search.trim()) }}><Stack spacing={1.5}><TextField label="Buscar equipamento" fullWidth value={search} onChange={(event) => setSearch(event.target.value)} slotProps={{ htmlInput: { maxLength: 200 } }} /><Button type="submit" variant="outlined" disabled={busy || loading}>Buscar</Button></Stack></Box>
        {loading && <LinearProgress aria-label="Carregando equipamentos" />}
        {!loading && !error && !models.length && <Box sx={{ p: 2 }}><EmptyState title={query ? 'Nenhum resultado' : 'Nenhum equipamento ativo'} description={query ? 'Experimente outro nome para encontrar o equipamento.' : 'Os modelos cadastrados aparecerão aqui.'} /></Box>}
        <Stack component="ul" spacing={0} divider={<Divider />} sx={{ listStyle: 'none', m: 0, p: 0 }}>
          {models.map((model) => <Box component="li" key={model.id} sx={{ minWidth: 0 }}><Button ref={(element) => { if (element) selectionButtons.current.set(model.id, element); else selectionButtons.current.delete(model.id) }} aria-label={`Ver unidades de ${model.name}`} aria-pressed={selected?.id === model.id} disabled={busy} onClick={() => void open(model)} sx={{ width: '100%', justifyContent: 'flex-start', textAlign: 'left', px: 2, py: 2.5, borderRadius: 0, borderLeft: '3px solid', borderColor: selected?.id === model.id ? 'primary.main' : 'transparent', bgcolor: selected?.id === model.id ? 'action.selected' : 'transparent', color: 'text.primary' }}><Box sx={{ minWidth: 0 }}><Typography component="span" variant="h4" sx={{ display: 'block', overflowWrap: 'anywhere' }}>{model.name}</Typography><Typography component="span" variant="body2" color="text.secondary" sx={{ display: 'block', mt: .5 }}>{model.active_quantity} unidades ativas no inventário</Typography></Box></Button></Box>)}
        </Stack>
        {cursor && <Box sx={{ p: 2 }}><Button fullWidth disabled={busy || loading} onClick={() => void load(cursor)}>Carregar mais equipamentos</Button></Box>}
      </Card>
      <Box sx={{ minWidth: 0, display: { xs: selected ? 'block' : 'none', lg: 'block' } }}>
        {!selected ? <Box sx={{ border: '1px dashed', borderColor: 'divider', borderRadius: 3, minHeight: 320, p: 4, display: 'grid', placeItems: 'center', textAlign: 'center' }}><Stack spacing={2} sx={{ alignItems: 'center', maxWidth: 330 }}><Box sx={{ color: 'primary.main' }}><EquipmentGlyph /></Box><Typography component="h2" variant="h3">Selecione um equipamento</Typography><Typography color="text.secondary">Veja suas unidades e sinalize quando alguma precisar ficar fora de serviço.</Typography></Stack></Box> : <Stack spacing={2}>
          <Box sx={{ display: { lg: 'none' } }}><Button disabled={busy} onClick={back}>Voltar aos equipamentos</Button></Box>
          <Card component="section" aria-labelledby="operational-units-title"><Box sx={{ p: { xs: 2, sm: 3 }, borderBottom: '1px solid', borderColor: 'divider' }}><Stack spacing={1.5}>
            <Typography variant="overline" color="primary">Unidades físicas</Typography><Typography id="operational-units-title" component="h2" variant="h3" ref={heading} tabIndex={-1} sx={{ fontSize: '1.6rem', overflowWrap: 'anywhere' }}>{selected.name}</Typography>
            <Stack direction="row" spacing={1} useFlexGap sx={{ flexWrap: 'wrap', alignItems: 'center', justifyContent: 'space-between' }}><Chip variant="outlined" label={`${selected.active_quantity} unidades ativas`} /><Button disabled={busy} onClick={() => void open(selected)}>Recarregar unidades</Button></Stack>
            <Typography color="text.secondary" variant="body2">O estado de funcionamento orienta novos planos de treino. A quantidade representa o inventário da academia.</Typography>
          </Stack></Box>
            {busy && <LinearProgress aria-label="Processando estado operacional" />}
            {!units.length ? <Box sx={{ p: 3 }}><EmptyState title="Nenhuma unidade cadastrada" description="O cadastro de unidades é realizado pela administração." /></Box> : <Stack divider={<Divider />}>
              {units.map((unit) => <Box key={unit.id} sx={{ p: { xs: 2, sm: 3 }, borderLeft: '3px solid', borderLeftColor: unit.active && unit.operational_state === 'out_of_order' ? 'warning.main' : 'transparent' }}><Stack spacing={1.5}>
                <Typography component="h3" variant="h4" sx={{ overflowWrap: 'anywhere' }}>{label(unit)}</Typography>
                <Stack direction="row" spacing={1} useFlexGap sx={{ flexWrap: 'wrap' }}><InventoryChip active={unit.active} /><OperationalChip state={unit.operational_state} /></Stack>
                {unit.active && <Box><Button variant="outlined" color={unit.operational_state === 'operational' ? 'warning' : 'success'} disabled={busy || stale} aria-label={`${action(unit)}: ${label(unit)}`} onClick={() => setConfirmation(unit)}>{action(unit)}</Button></Box>}
              </Stack></Box>)}
            </Stack>}
            {unitCursor && <Box sx={{ p: 2 }}><Button fullWidth disabled={busy} onClick={() => void open(selected, unitCursor)}>Carregar mais unidades</Button></Box>}
          </Card>
        </Stack>}
      </Box>
    </Box>
    {busy && !selected && <LoadingState label="Carregando unidades" />}
    <Dialog open={!!confirmation} onClose={() => { if (!busy) setConfirmation(null) }} aria-labelledby="estado-operacional-titulo" aria-describedby="estado-operacional-descricao">
      <DialogTitle id="estado-operacional-titulo">{confirmation && action(confirmation)}</DialogTitle><DialogContent><DialogContentText id="estado-operacional-descricao">Confirmar a mudança de estado de {confirmation && label(confirmation)}?</DialogContentText><Typography variant="body2" color="text.secondary" sx={{ mt: 2 }}>O inventário e os planos já aprovados serão preservados.</Typography></DialogContent>
      <DialogActions><Button autoFocus disabled={busy} onClick={() => setConfirmation(null)}>Cancelar</Button><Button disabled={busy} variant="contained" onClick={() => void toggle()}>Confirmar alteração</Button></DialogActions>
    </Dialog>
  </Stack></InstructorShell>
}
