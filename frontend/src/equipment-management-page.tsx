import { Alert, Box, Button, Card, Chip, Dialog, DialogActions, DialogContent, DialogTitle, Divider, Drawer, MenuItem, Stack, Tab, Tabs, TextField, Typography } from '@mui/material'
import { useEffect, useRef, useState } from 'react'
import { AdminShell } from './components/application-shell'
import { EquipmentPhoto, EquipmentStats, InventoryChip, OperationalChip } from './components/equipment-presentation'
import { RouterButtonLink } from './components/router-button-link'
import { EmptyState, LoadingState, PageHeader, StatusNotice } from './components/ui'
import { EquipmentEditor } from './equipment-editor'
import { createEquipmentUnits, getEquipmentModels, getEquipmentUnits, updateEquipmentModel, updateEquipmentUnit, type EquipmentAdminModel, type EquipmentUnit } from './equipment'

type Props = { accessToken: string; onSignOut: () => void }
const normalized = (value: string) => value.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLocaleLowerCase('pt-BR')
export function EquipmentManagementPage({ accessToken, onSignOut }: Props) {
  const [models, setModels] = useState<EquipmentAdminModel[]>([])
  const [loading, setLoading] = useState(true)
  const [selected, setSelected] = useState<EquipmentAdminModel | null>(null)
  const [units, setUnits] = useState<EquipmentUnit[] | null>(null)
  const [unitsError, setUnitsError] = useState<string | null>(null)
  const [search, setSearch] = useState('')
  const [status, setStatus] = useState('all')
  const [tab, setTab] = useState(0)
  const [editor, setEditor] = useState<{ model: EquipmentAdminModel | null } | null>(null)
  const [unitEditor, setUnitEditor] = useState<EquipmentUnit | null>(null)
  const [unitForm, setUnitForm] = useState({ label: '', location: '', serial_number: '' })
  const [batch, setBatch] = useState(false)
  const [quantity, setQuantity] = useState('1')
  const [prefix, setPrefix] = useState('UN')
  const [confirmation, setConfirmation] = useState<{ model?: EquipmentAdminModel; unit?: EquipmentUnit } | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [operationError, setOperationError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const working = useRef(false)
  const unitsRequest = useRef(0)
  const modelsRequest = useRef(0)
  const report = (reason: unknown) => reason instanceof Error ? reason.message : 'Não foi possível concluir esta ação.'
  async function loadModels() {
    const request = ++modelsRequest.current
    setLoading(true); setError(null)
    try { const items = await getEquipmentModels(accessToken); if (request === modelsRequest.current) { setModels(items); setSelected((old) => items.find((item) => item.id === old?.id) ?? null) } }
    catch (reason) { if (request === modelsRequest.current) setError(report(reason)) }
    finally { if (request === modelsRequest.current) setLoading(false) }
  }
  useEffect(() => { void loadModels(); return () => { modelsRequest.current++; unitsRequest.current++ } }, [accessToken])
  async function loadUnits(model: EquipmentAdminModel) {
    const request = ++unitsRequest.current
    setUnits(null); setUnitsError(null)
    try { const items = await getEquipmentUnits(accessToken, model.id); if (request === unitsRequest.current) setUnits(items.sort((a, b) => (a.label || '').localeCompare(b.label || '', 'pt-BR', { numeric: true }))) }
    catch (reason) { if (request === unitsRequest.current) { setUnitsError(report(reason)); setUnits([]) } }
  }
  function openDetails(model: EquipmentAdminModel) { setSelected(model); setTab(0); setOperationError(null); void loadUnits(model) }
  function upsert(model: EquipmentAdminModel) {
    modelsRequest.current++; setLoading(false)
    setModels((old) => [...old.filter((item) => item.id !== model.id), model].sort((a, b) => a.name.localeCompare(b.name, 'pt-BR')))
    setSelected(model)
  }
  async function perform(action: () => Promise<void>) {
    if (working.current) return
    working.current = true; setBusy(true); setOperationError(null); setNotice(null)
    try { await action() } catch (reason) { setOperationError(report(reason)) }
    finally { working.current = false; setBusy(false) }
  }
  async function toggleConfirmed() {
    if (!confirmation) return
    await perform(async () => {
      if (confirmation.model) { const model = await updateEquipmentModel(accessToken, confirmation.model.id, { active: !confirmation.model.active }); upsert(model) }
      if (confirmation.unit && selected) {
        const updated = await updateEquipmentUnit(accessToken, confirmation.unit.id, { active: !confirmation.unit.active })
        setUnits((old) => old?.map((unit) => unit.id === updated.id ? updated : unit) ?? null)
        upsert({ ...selected, active_quantity: selected.active_quantity + (updated.active ? 1 : -1) })
      }
      setConfirmation(null); setNotice('Estado do inventário atualizado.')
    })
  }
  const filtered = models.filter((model) => (status === 'all' || model.active === (status === 'active')) && normalized([model.name, model.brand, model.manufacturer_model, model.category].filter(Boolean).join(' ')).includes(normalized(search)))
  const active = models.filter((model) => model.active)
  const selectedUnits = units ?? []
  return <AdminShell onSignOut={onSignOut}><Stack spacing={3} sx={{ minWidth: 0 }}>
    <PageHeader eyebrow="Inventário da academia" title="Gerenciar equipamentos" description="Organize o catálogo e acompanhe cada unidade física." action={<Button variant="contained" disabled={loading || busy} onClick={() => { setSelected(null); setEditor({ model: null }) }}>Novo equipamento</Button>} />
    <EquipmentStats items={[{ label: 'Modelos ativos', value: active.length }, { label: 'Unidades ativas', value: active.reduce((sum, model) => sum + model.active_quantity, 0) }, { label: 'Modelos inativos', value: models.length - active.length }]} />
    {error && <StatusNotice severity="error">{error}</StatusNotice>}{notice && <StatusNotice severity="success">{notice}</StatusNotice>}
    <Card><Box sx={{ p: { xs: 2, sm: 2.5 }, borderBottom: '1px solid', borderColor: 'divider' }}><Stack direction={{ xs: 'column', sm: 'row' }} spacing={2}>
      <TextField fullWidth label="Buscar equipamento" placeholder="Nome, marca ou categoria" value={search} onChange={(event) => setSearch(event.target.value)} />
      <TextField select label="Estado do catálogo" value={status} onChange={(event) => setStatus(event.target.value)} sx={{ minWidth: { sm: 190 } }}><MenuItem value="all">Todos</MenuItem><MenuItem value="active">Ativos</MenuItem><MenuItem value="inactive">Inativos</MenuItem></TextField>
      <Button disabled={loading || busy} onClick={() => void loadModels()}>Recarregar</Button>
    </Stack></Box>
      {loading ? <LoadingState label="Carregando equipamentos" /> : !filtered.length ? <Box sx={{ p: 3 }}><EmptyState title={models.length ? 'Nenhum resultado' : 'Nenhum equipamento cadastrado'} description={models.length ? 'Experimente outro nome ou altere os filtros.' : 'Comece cadastrando um equipamento e suas unidades físicas.'} /></Box> : <Box component="ul" sx={{ m: 0, p: 0, listStyle: 'none' }}>
        {filtered.map((model, index) => <Box component="li" key={model.id} sx={{ p: { xs: 2, sm: 2.5 }, borderTop: index ? '1px solid' : 0, borderColor: 'divider', '&:hover': { bgcolor: 'action.hover' } }}>
          <Box sx={{ display: 'grid', gridTemplateColumns: { xs: 'minmax(0, 1fr) auto', md: 'minmax(0, 1fr) auto auto auto' }, alignItems: 'center', columnGap: 3, rowGap: 1 }}>
            <Stack direction="row" spacing={2} sx={{ alignItems: 'center', minWidth: 0, gridColumn: { xs: '1 / -1', md: 'auto' } }}><EquipmentPhoto compact url={model.image_url} name={model.name} token={accessToken} revision={model.updated_at} /><Box sx={{ minWidth: 0 }}><Typography component="h2" variant="h3" sx={{ overflowWrap: 'anywhere' }}>{model.name}</Typography><Typography color="text.secondary" variant="body2" sx={{ mt: .5, overflowWrap: 'anywhere' }}>{[model.category, model.brand].filter(Boolean).join(' · ') || 'Sem categoria'}</Typography></Box></Stack>
            <Typography variant="body2" color="text.secondary">{model.active_quantity} {model.active_quantity === 1 ? 'unidade ativa' : 'unidades ativas'}{!model.active && <Box component="span" sx={{ display: { md: 'none' } }}> · Inativo</Box>}</Typography>
            <Box sx={{ display: { xs: 'none', md: 'block' } }}><Chip size="small" variant="outlined" label={model.active ? 'No catálogo' : 'Inativo'} color={model.active ? 'success' : 'default'} /></Box>
            <Button disabled={busy} aria-label={`Ver detalhes de ${model.name}`} onClick={() => openDetails(model)}>Ver detalhes</Button>
          </Box>
        </Box>)}
      </Box>}
    </Card>
    <Box><RouterButtonLink to="/admin" variant="text">Voltar ao painel</RouterButtonLink></Box>
    <Drawer anchor="right" open={!!selected} onClose={() => { if (!busy) { setSelected(null); unitsRequest.current++ } }} slotProps={{ paper: { sx: { width: { xs: '100%', sm: 620 }, maxWidth: '100%' }, role: 'dialog', 'aria-modal': true, 'aria-labelledby': 'equipment-detail-title' } }}>
      {selected && <Stack sx={{ minHeight: '100%', minWidth: 0 }}>
        <Box sx={{ p: 3 }}><Stack direction="row" spacing={1} sx={{ alignItems: 'center', justifyContent: 'space-between' }}><Typography variant="overline" color="primary">Detalhes do equipamento</Typography><Button disabled={busy} onClick={() => { setSelected(null); unitsRequest.current++ }}>Fechar detalhes</Button></Stack><Typography id="equipment-detail-title" component="h2" variant="h3" sx={{ fontSize: '1.65rem', mt: 1, overflowWrap: 'anywhere' }}>{selected.name}</Typography></Box>
        <Tabs value={tab} onChange={(_, value) => setTab(value)} aria-label="Detalhes do equipamento" variant="fullWidth" sx={{ borderBottom: '1px solid', borderColor: 'divider' }}><Tab label="Visão geral" /><Tab label={`Unidades físicas (${selectedUnits.length})`} /></Tabs>
        <Box sx={{ p: { xs: 2, sm: 3 }, flex: 1 }}>
          {notice && <Alert severity="success" sx={{ mb: 2 }}>{notice}</Alert>}
          {tab === 0 ? <Stack spacing={2.5}>
            <Box sx={{ borderRadius: 2, overflow: 'hidden' }}><EquipmentPhoto url={selected.image_url} name={selected.name} token={accessToken} revision={selected.updated_at} height={230} /></Box>
            <Stack direction="row" spacing={1} useFlexGap sx={{ flexWrap: 'wrap' }}><Chip variant="outlined" color={selected.active ? 'success' : 'default'} label={selected.active ? 'Visível no catálogo' : 'Oculto do catálogo'} /><Chip variant="outlined" label={`${selected.active_quantity} unidades ativas`} /></Stack>
            <Typography color="text.secondary" sx={{ whiteSpace: 'pre-wrap', overflowWrap: 'anywhere' }}>{selected.description || 'Adicione uma descrição para apresentar este equipamento no catálogo.'}</Typography>
            <Divider /><Box><Typography component="h3" variant="h4">Informações internas</Typography><Typography variant="body2" color="text.secondary">Visíveis apenas para administradores.</Typography></Box>
            <Box component="dl" sx={{ m: 0, display: 'grid', gridTemplateColumns: 'minmax(0, 1fr) minmax(0, 1.3fr)', gap: 1.5 }}>{[['Marca', selected.brand], ['Modelo do fabricante', selected.manufacturer_model], ['Categoria', selected.category]].map(([label, value]) => <Box key={label} sx={{ display: 'contents' }}><Typography component="dt" color="text.secondary" variant="body2">{label}</Typography><Typography component="dd" variant="body2" sx={{ m: 0, overflowWrap: 'anywhere' }}>{value || 'Não informado'}</Typography></Box>)}</Box>
            <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1}><Button variant="contained" disabled={busy} onClick={() => setEditor({ model: selected })}>Editar equipamento</Button><Button color={selected.active ? 'warning' : 'success'} variant="outlined" disabled={busy} onClick={() => { setOperationError(null); setConfirmation({ model: selected }) }}>{selected.active ? 'Desativar modelo' : 'Reativar modelo'}</Button></Stack>
          </Stack> : <Stack spacing={2}>
            <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1} sx={{ justifyContent: 'space-between' }}><Button variant="contained" disabled={busy} onClick={() => { setQuantity('1'); setPrefix('UN'); setOperationError(null); setBatch(true) }}>Adicionar unidades</Button><Button disabled={busy || !units} onClick={() => void loadUnits(selected)}>Recarregar unidades</Button></Stack>
            <Typography color="text.secondary" variant="body2">Inventário e funcionamento são estados independentes. O instrutor atualiza a condição de uso.</Typography>
            {unitsError && <Alert severity="error">{unitsError}</Alert>}
            {!units ? <LoadingState label="Carregando unidades" /> : !units.length ? <EmptyState title="Nenhuma unidade cadastrada" description="Adicione as unidades físicas deste equipamento." /> : <Stack divider={<Divider />}>
              {units.map((unit, index) => <Stack key={unit.id} spacing={1.5} sx={{ py: 2 }}><Typography component="h3" variant="h4" sx={{ overflowWrap: 'anywhere' }}>{unit.label || `Unidade ${index + 1}`}</Typography><Stack direction="row" spacing={1} useFlexGap sx={{ flexWrap: 'wrap' }}><InventoryChip active={unit.active} /><OperationalChip state={unit.operational_state} /></Stack>
                {(unit.location || unit.serial_number) && <Typography color="text.secondary" variant="body2" sx={{ overflowWrap: 'anywhere' }}>{unit.location && `Local: ${unit.location}`}{unit.location && unit.serial_number && ' · '}{unit.serial_number && `Série: ${unit.serial_number}`}</Typography>}
                <Stack direction="row" spacing={1} useFlexGap sx={{ flexWrap: 'wrap' }}><Button disabled={busy} aria-label={`Editar ${unit.label || `unidade ${index + 1}`}`} onClick={() => { setUnitEditor(unit); setUnitForm({ label: unit.label || '', location: unit.location || '', serial_number: unit.serial_number || '' }); setOperationError(null) }}>Editar detalhes</Button><Button disabled={busy} color={unit.active ? 'warning' : 'success'} aria-label={`${unit.active ? 'Desativar' : 'Reativar'} ${unit.label || `unidade ${index + 1}`}`} onClick={() => { setOperationError(null); setConfirmation({ unit }) }}>{unit.active ? 'Desativar' : 'Reativar'}</Button></Stack>
              </Stack>)}
            </Stack>}
          </Stack>}
        </Box>
      </Stack>}
    </Drawer>
    {editor && <EquipmentEditor key={editor.model?.id || 'new'} token={accessToken} model={editor.model} onClose={() => setEditor(null)} onSaved={(model) => { upsert(model); setEditor(null); setNotice('Equipamento salvo com sucesso.'); setTab(0); void loadUnits(model) }} />}
    <Dialog open={batch} onClose={() => { if (!busy) setBatch(false) }} fullWidth maxWidth="xs" aria-labelledby="equipment-batch-title"><DialogTitle id="equipment-batch-title">Adicionar unidades</DialogTitle><DialogContent><Stack spacing={2} sx={{ pt: 1 }}>
      {operationError && <Alert severity="error">{operationError}</Alert>}<Typography color="text.secondary">Os próximos identificadores livres serão usados automaticamente.</Typography><TextField label="Quantidade" type="number" value={quantity} onChange={(event) => setQuantity(event.target.value)} disabled={busy} slotProps={{ htmlInput: { min: 1, max: 100, step: 1 } }} helperText="Entre 1 e 100 unidades." /><TextField label="Prefixo" value={prefix} disabled={busy} onChange={(event) => setPrefix(event.target.value)} slotProps={{ htmlInput: { maxLength: 40 } }} helperText="Exemplo: EST gera EST-01, EST-02…" />
    </Stack></DialogContent><DialogActions><Button disabled={busy} onClick={() => setBatch(false)}>Cancelar</Button><Button variant="contained" disabled={busy || !Number.isInteger(Number(quantity)) || Number(quantity) < 1 || Number(quantity) > 100} onClick={() => void perform(async () => { if (!selected) return; const created = await createEquipmentUnits(accessToken, selected.id, Number(quantity), prefix || 'UN'); upsert({ ...selected, active_quantity: selected.active_quantity + created.length }); setBatch(false); setNotice('Unidades adicionadas.'); await loadUnits(selected) })}>{busy ? 'Adicionando...' : 'Adicionar'}</Button></DialogActions></Dialog>
    <Dialog open={!!unitEditor} onClose={() => { if (!busy) setUnitEditor(null) }} fullWidth maxWidth="sm" aria-labelledby="equipment-unit-title"><DialogTitle id="equipment-unit-title">Editar unidade</DialogTitle><DialogContent><Stack spacing={2} sx={{ pt: 1 }}>{operationError && <Alert severity="error">{operationError}</Alert>}<Typography color="text.secondary" variant="body2">Localização e número de série são visíveis apenas para administradores.</Typography>{([['label', 'Identificador interno', 200], ['location', 'Localização na academia', 120], ['serial_number', 'Número de série', 120]] as const).map(([key, label, maximum]) => <TextField key={key} label={label} fullWidth disabled={busy} value={unitForm[key]} onChange={(event) => setUnitForm((old) => ({ ...old, [key]: event.target.value }))} slotProps={{ htmlInput: { maxLength: maximum } }} />)}</Stack></DialogContent><DialogActions><Button disabled={busy} onClick={() => setUnitEditor(null)}>Cancelar</Button><Button disabled={busy} variant="contained" onClick={() => void perform(async () => { if (!unitEditor) return; const updated = await updateEquipmentUnit(accessToken, unitEditor.id, unitForm); setUnits((old) => old?.map((unit) => unit.id === updated.id ? updated : unit) ?? null); setUnitEditor(null); setNotice('Detalhes da unidade atualizados.') })}>{busy ? 'Salvando...' : 'Salvar unidade'}</Button></DialogActions></Dialog>
    <Dialog open={!!confirmation} onClose={() => { if (!busy) setConfirmation(null) }} aria-labelledby="equipment-state-title"><DialogTitle id="equipment-state-title">Confirmar alteração no inventário</DialogTitle><DialogContent><Stack spacing={2}>{operationError && <Alert severity="error">{operationError}</Alert>}<Typography>{confirmation?.model ? confirmation.model.active ? 'Este modelo ficará oculto no catálogo e deixará de ser uma opção para novos planos. Os registros e planos existentes serão preservados.' : 'Este modelo voltará a aparecer no catálogo.' : confirmation?.unit?.active ? 'Esta unidade deixará de contar no total ativo. Seu registro será preservado.' : 'Esta unidade voltará a contar no total ativo. Seu estado de funcionamento será mantido.'}</Typography></Stack></DialogContent><DialogActions><Button autoFocus disabled={busy} onClick={() => setConfirmation(null)}>Cancelar</Button><Button disabled={busy} variant="contained" onClick={() => void toggleConfirmed()}>{busy ? 'Atualizando...' : 'Confirmar alteração'}</Button></DialogActions></Dialog>
  </Stack></AdminShell>
}
