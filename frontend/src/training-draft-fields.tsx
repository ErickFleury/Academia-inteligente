import { Button, Card, CardContent, MenuItem, Stack, TextField, Typography } from '@mui/material'
import { useEffect, useState } from 'react'
import { getUsableEquipment, type UsableEquipmentModel } from './instructor-equipment'
import { StatusNotice } from './components/ui'
import type { ReviewContent, ReviewItem } from './training-review'
const emptyItem = (): ReviewItem => ({ exercise_name: '', sets: 3, repetitions: '', load_guidance: '', rest_seconds: 60, equipment_requirement: null, equipment_model_id: null })
export function TrainingDraftFields({ accessToken, draft, onChange }: { accessToken: string; draft: ReviewContent; onChange: (value: ReviewContent) => void }) {
  const [models, setModels] = useState<UsableEquipmentModel[]>([])
  const [cursor, setCursor] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)
  async function load(next?: string) {
    setLoading(true); setError(false)
    try { const page = await getUsableEquipment(accessToken, next); setModels((old) => next ? [...old, ...page.items.filter((item) => !old.some((model) => model.id === item.id))] : page.items); setCursor(page.next_cursor) }
    catch { setError(true) }
    finally { setLoading(false) }
  }
  useEffect(() => { void load() }, [accessToken])
  function changeItem(index: number, changes: Partial<ReviewItem>) { onChange({ ...draft, items: draft.items.map((item, position) => position === index ? { ...item, ...changes } : item) }) }
  function move(index: number, delta: number) { const items = [...draft.items]; [items[index], items[index + delta]] = [items[index + delta], items[index]]; onChange({ ...draft, items }) }
  return <Stack spacing={2}>
        {error && <StatusNotice severity="error">Não foi possível consultar os equipamentos para prescrição. Recarregue a lista.</StatusNotice>}
        <Button disabled={loading} onClick={() => void load()}>Recarregar equipamentos para prescrição</Button>
        {loading && <Typography role="status">Consultando equipamentos para prescrição…</Typography>}
        {cursor && <Button disabled={loading} onClick={() => void load(cursor)}>Carregar mais opções de equipamento</Button>}
        <TextField required fullWidth label="Nome do plano" value={draft.name} onChange={(event) => onChange({ ...draft, name: event.target.value })} />
        <TextField required fullWidth multiline label="Objetivo" value={draft.objective} onChange={(event) => onChange({ ...draft, objective: event.target.value })} />
        {draft.items.map((item, index) => <Card key={index} variant="outlined"><CardContent><Stack spacing={1.5}>
          <Typography component="h3" variant="h4">Exercício {index + 1}</Typography>
          <TextField required label={`Nome do exercício ${index + 1}`} value={item.exercise_name} onChange={(event) => changeItem(index, { exercise_name: event.target.value })} />
          <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1}>
            <TextField fullWidth required label={`Séries ${index + 1}`} type="number" value={item.sets} onChange={(event) => changeItem(index, { sets: Number(event.target.value) })} />
            <TextField fullWidth required label={`Repetições ${index + 1}`} value={item.repetitions} onChange={(event) => changeItem(index, { repetitions: event.target.value })} />
          </Stack>
          <TextField required label={`Orientação de carga ${index + 1}`} value={item.load_guidance} onChange={(event) => changeItem(index, { load_guidance: event.target.value })} />
          <TextField required label={`Descanso em segundos ${index + 1}`} type="number" value={item.rest_seconds} onChange={(event) => changeItem(index, { rest_seconds: Number(event.target.value) })} />
          {item.equipment_model_id && <Typography>Referência preservada: {item.equipment_requirement ?? 'Equipamento do catálogo'}</Typography>}
          <TextField select disabled={loading || error} label={`Equipamento do catálogo ${index + 1}`} value={item.equipment_model_id ?? ''} helperText="Novas escolhas exigem modelo ativo com unidade operacional. A referência preservada só pode ser mantida sem alterar o item aprovado." onChange={(event) => { const model = models.find((value) => value.id === event.target.value); changeItem(index, { equipment_model_id: model?.id ?? null, equipment_requirement: model?.name ?? null }) }}>
            <MenuItem value="">Sem equipamento do catálogo</MenuItem>
            {item.equipment_model_id && !models.some((model) => model.id === item.equipment_model_id) && <MenuItem disabled value={item.equipment_model_id}>{item.equipment_requirement ?? 'Referência preservada'}</MenuItem>}
            {models.map((model) => <MenuItem key={model.id} value={model.id}>{model.name}</MenuItem>)}
          </TextField>
          <Stack direction="row" sx={{ flexWrap: 'wrap', gap: 1 }}>
            <Button disabled={index === 0} aria-label={`Mover exercício ${index + 1} para cima`} onClick={() => move(index, -1)}>Subir</Button>
            <Button disabled={index === draft.items.length - 1} aria-label={`Mover exercício ${index + 1} para baixo`} onClick={() => move(index, 1)}>Descer</Button>
            <Button color="error" disabled={draft.items.length === 1} onClick={() => onChange({ ...draft, items: draft.items.filter((_, position) => position !== index) })}>Remover exercício {index + 1}</Button>
          </Stack>
        </Stack></CardContent></Card>)}
        <Button disabled={draft.items.length >= 100} onClick={() => onChange({ ...draft, items: [...draft.items, emptyItem()] })}>Adicionar exercício</Button>
  </Stack>
}
