import { Button, Card, CardContent, Divider, Stack, TextField, Typography } from '@mui/material'
import { useEffect, useState } from 'react'

import { AdminShell } from './components/application-shell'
import { RouterButtonLink } from './components/router-button-link'
import { EmptyState, LoadingState, PageHeader, StatusNotice } from './components/ui'
import {
  createEquipmentModel,
  createEquipmentUnit,
  getEquipmentModels,
  getEquipmentUnits,
  updateEquipmentModel,
  updateEquipmentUnit,
  type EquipmentAdminModel,
  type EquipmentUnit,
} from './equipment'

type Props = { accessToken: string; onSignOut: () => void }

export function EquipmentManagementPage({ accessToken, onSignOut }: Props) {
  const [models, setModels] = useState<EquipmentAdminModel[] | null>(null)
  const [selected, setSelected] = useState<EquipmentAdminModel | null>(null)
  const [units, setUnits] = useState<EquipmentUnit[] | null>(null)
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [imageUrl, setImageUrl] = useState('')
  const [unitLabel, setUnitLabel] = useState('')
  const [editingId, setEditingId] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)

  const loadModels = () => {
    setModels(null)
    void getEquipmentModels(accessToken)
      .then((items) => {
        setModels(items)
        setSelected((current) => items.find((item) => item.id === current?.id) ?? null)
      })
      .catch((reason: unknown) => {
        setError(reason instanceof Error ? reason.message : 'Não foi possível carregar os equipamentos.')
        setModels([])
      })
  }
  const loadUnits = (model: EquipmentAdminModel) => {
    setSelected(model); setUnits(null)
    void getEquipmentUnits(accessToken, model.id).then(setUnits).catch((reason: unknown) => {
      setError(reason instanceof Error ? reason.message : 'Não foi possível carregar as unidades.')
      setUnits([])
    })
  }
  useEffect(loadModels, [accessToken])

  function resetModelForm() { setEditingId(null); setName(''); setDescription(''); setImageUrl('') }
  async function saveModel() {
    setError(null); setSuccess(null)
    try {
      if (editingId) await updateEquipmentModel(accessToken, editingId, { name, description, image_url: imageUrl })
      else await createEquipmentModel(accessToken, { name, description, image_url: imageUrl })
      resetModelForm(); setSuccess(editingId ? 'Equipamento atualizado.' : 'Modelo de equipamento criado.'); loadModels()
    } catch (reason) { setError(reason instanceof Error ? reason.message : 'Não foi possível salvar o equipamento.') }
  }
  async function toggleModel(model: EquipmentAdminModel) {
    try { await updateEquipmentModel(accessToken, model.id, { active: !model.active }); setSuccess('Estado do equipamento atualizado.'); loadModels() }
    catch (reason) { setError(reason instanceof Error ? reason.message : 'Não foi possível atualizar o equipamento.') }
  }
  async function addUnit() {
    if (!selected) return
    try { await createEquipmentUnit(accessToken, selected.id, unitLabel); setUnitLabel(''); setSuccess('Unidade física adicionada.'); loadModels(); loadUnits(selected) }
    catch (reason) { setError(reason instanceof Error ? reason.message : 'Não foi possível adicionar a unidade.') }
  }
  async function toggleUnit(unit: EquipmentUnit) {
    try { await updateEquipmentUnit(accessToken, unit.id, { active: !unit.active }); setSuccess('Estado da unidade atualizado.'); if (selected) { loadModels(); loadUnits(selected) } }
    catch (reason) { setError(reason instanceof Error ? reason.message : 'Não foi possível atualizar a unidade.') }
  }

  return <AdminShell onSignOut={onSignOut}><Stack spacing={3} sx={{ minWidth: 0 }}>
    <PageHeader action={<RouterButtonLink to="/admin" variant="outlined">Voltar ao painel</RouterButtonLink>} eyebrow="Catálogo" title="Gerenciar equipamentos" description="Cadastre modelos e suas unidades físicas. “Ativa” indica presença no catálogo, não disponibilidade imediata." />
    {error && <StatusNotice severity="error">{error}</StatusNotice>}{success && <StatusNotice severity="success">{success}</StatusNotice>}
    <Card component="form" onSubmit={(event) => { event.preventDefault(); void saveModel() }}><CardContent><Stack spacing={2}>
      <Typography component="h2" variant="h4">{editingId ? 'Editar modelo' : 'Novo modelo de equipamento'}</Typography>
      <TextField fullWidth label="Nome do modelo" onChange={(event) => setName(event.target.value)} required value={name} />
      <TextField fullWidth label="Informações adicionais" multiline minRows={2} onChange={(event) => setDescription(event.target.value)} value={description} />
      <TextField fullWidth helperText="Use somente imagens licenciadas ou aprovadas pela academia." label="Referência da imagem (opcional)" onChange={(event) => setImageUrl(event.target.value)} value={imageUrl} />
      <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1}><Button type="submit" variant="contained">{editingId ? 'Salvar alterações' : 'Criar modelo'}</Button>{editingId && <Button onClick={resetModelForm} variant="text">Cancelar edição</Button>}</Stack>
    </Stack></CardContent></Card>
    {!models ? <LoadingState label="Carregando equipamentos" /> : models.length === 0 ? <EmptyState title="Nenhum modelo cadastrado" description="Crie um modelo e registre as unidades físicas existentes." /> : <Stack spacing={2}>
      {models.map((model) => <Card key={model.id}><CardContent><Stack spacing={1.5}>
        <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1} sx={{ justifyContent: 'space-between' }}><div><Typography component="h2" variant="h4">{model.name}</Typography><Typography color="text.secondary" variant="body2">{model.active ? `${model.active_quantity} unidades ativas` : 'Modelo inativo e oculto do catálogo público'}</Typography></div><Stack direction={{ xs: 'column', sm: 'row' }} spacing={1}><Button onClick={() => { setEditingId(model.id); setName(model.name); setDescription(model.description ?? ''); setImageUrl(model.image_url ?? '') }} variant="outlined">Editar</Button><Button color={model.active ? 'warning' : 'success'} onClick={() => void toggleModel(model)} variant="outlined">{model.active ? 'Desativar' : 'Reativar'}</Button><Button onClick={() => loadUnits(model)} variant="contained">Unidades</Button></Stack></Stack>
        {model.description && <Typography color="text.secondary">{model.description}</Typography>}
      </Stack></CardContent></Card>)}
    </Stack>}
    {selected && <Card component="section"><CardContent><Stack spacing={2}><Typography component="h2" variant="h4">Unidades físicas — {selected.name}</Typography><Typography color="text.secondary" variant="body2">O total ativo é calculado automaticamente a partir destas unidades.</Typography><Divider />
      <Stack component="form" direction={{ xs: 'column', sm: 'row' }} spacing={1} onSubmit={(event) => { event.preventDefault(); void addUnit() }}><TextField fullWidth label="Identificador interno (opcional)" onChange={(event) => setUnitLabel(event.target.value)} value={unitLabel} /><Button type="submit" variant="contained">Adicionar unidade</Button></Stack>
      {!units ? <LoadingState label="Carregando unidades" /> : units.length === 0 ? <EmptyState title="Nenhuma unidade registrada" description="Adicione cada máquina física deste modelo." /> : units.map((unit, index) => <Stack direction={{ xs: 'column', sm: 'row' }} key={unit.id} spacing={1} sx={{ alignItems: { sm: 'center' }, justifyContent: 'space-between' }}><Typography>{unit.label || `Unidade ${index + 1}`}</Typography><Button color={unit.active ? 'warning' : 'success'} onClick={() => void toggleUnit(unit)} variant="outlined">{unit.active ? 'Desativar unidade' : 'Reativar unidade'}</Button></Stack>)}
    </Stack></CardContent></Card>}
  </Stack></AdminShell>
}
