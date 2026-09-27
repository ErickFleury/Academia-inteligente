import { Alert, Box, Button, Dialog, DialogActions, DialogContent, DialogTitle, Divider, Stack, Step, StepLabel, Stepper, Tab, Tabs, TextField, Typography, useMediaQuery, useTheme } from '@mui/material'
import { useEffect, useRef, useState } from 'react'
import { EquipmentPhoto } from './components/equipment-presentation'
import { createEquipmentModel, EquipmentRequestError, updateEquipmentModel, uploadEquipmentImage, type EquipmentAdminModel, type EquipmentModelInput } from './equipment'

type Props = { token: string; model: EquipmentAdminModel | null; onClose: () => void; onSaved: (model: EquipmentAdminModel) => void }
export function EquipmentEditor({ token, model, onClose, onSaved }: Props) {
  const theme = useTheme()
  const fullScreen = useMediaQuery(theme.breakpoints.down('sm'))
  const [savedModel, setSavedModel] = useState(model)
  const [step, setStep] = useState(0)
  const [form, setForm] = useState({ name: model?.name ?? '', description: model?.description ?? '', brand: model?.brand ?? '', manufacturer_model: model?.manufacturer_model ?? '', category: model?.category ?? '', image_url: model?.image_link ?? (model?.image_source !== 'upload' ? model?.image_url ?? '' : ''), initial_quantity: '1', unit_prefix: 'UN' })
  const [photoMode, setPhotoMode] = useState(model?.image_source === 'link' || (!model?.image_source && model?.image_url) ? 'link' : 'upload')
  const [file, setFile] = useState<File | null>(null)
  const [preview, setPreview] = useState<string | null>(null)
  const [removedPhoto, setRemovedPhoto] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [errors, setErrors] = useState<Record<string, string>>({})
  const [discard, setDiscard] = useState(false)
  const dirty = useRef(false)
  const working = useRef(false)
  useEffect(() => {
    if (!file) { setPreview(null); return }
    const url = URL.createObjectURL(file); setPreview(url)
    return () => URL.revokeObjectURL(url)
  }, [file])
  function change(key: keyof typeof form, value: string) { dirty.current = true; setForm((old) => ({ ...old, [key]: value })); setErrors((old) => ({ ...old, [key]: '' })) }
  function validate() {
    const next: Record<string, string> = {}
    if (!form.name.trim()) next.name = 'Informe o nome do equipamento.'
    if (photoMode === 'link' && form.image_url && !/^(https?:\/\/[^\s/]+|\/[^/\\])/.test(form.image_url)) next.image_url = 'Use um link http/https ou um caminho iniciado por /.'
    if (!savedModel && (!Number.isInteger(Number(form.initial_quantity)) || Number(form.initial_quantity) < 1 || Number(form.initial_quantity) > 100)) next.initial_quantity = 'Informe uma quantidade entre 1 e 100.'
    setErrors(next); return Object.keys(next).length === 0
  }
  const close = () => { if (!busy) { if (dirty.current) setDiscard(true); else onClose() } }
  async function save() {
    if (working.current || !validate()) return
    working.current = true; setBusy(true); setError(null)
    let photoPending = false
    try {
      const input: EquipmentModelInput = { name: form.name.trim(), description: form.description, brand: form.brand || null, manufacturer_model: form.manufacturer_model || null, category: form.category || null }
      if (photoMode === 'link' || removedPhoto) input.image_url = photoMode === 'link' ? form.image_url : ''
      let result = savedModel ? await updateEquipmentModel(token, savedModel.id, input) : await createEquipmentModel(token, { ...input, initial_quantity: Number(form.initial_quantity), unit_prefix: form.unit_prefix || 'UN' })
      setSavedModel(result)
      if (photoMode === 'upload' && file) { photoPending = true; result = await uploadEquipmentImage(token, result.id, file) }
      dirty.current = false; onSaved(result)
    } catch (reason) {
      const message = reason instanceof Error ? reason.message : 'Não foi possível salvar o equipamento.'
      setError(photoPending ? `Equipamento e unidades salvos. A foto ainda não foi salva. ${message} Tente salvar novamente para concluir a foto.` : message)
      if (reason instanceof EquipmentRequestError) setErrors(reason.fields)
    } finally { working.current = false; setBusy(false) }
  }
  const field = (key: keyof typeof form, label: string, maximum: number, required = false) => <TextField fullWidth label={label} value={form[key]} required={required} disabled={busy} error={!!errors[key]} helperText={errors[key]} onChange={(event) => change(key, event.target.value)} slotProps={{ htmlInput: { maxLength: maximum } }} />
  const photoUrl = photoMode === 'link' ? form.image_url : preview || (!removedPhoto && model?.image_source === 'upload' ? model.image_url : null)
  return <>
    <Dialog open onClose={close} fullScreen={fullScreen} fullWidth maxWidth="md" slotProps={{ paper: { sx: { backgroundImage: 'none' } } }} aria-labelledby="equipment-editor-title">
      <DialogTitle id="equipment-editor-title">{savedModel ? 'Editar equipamento' : 'Novo equipamento'}</DialogTitle>
      <DialogContent dividers>
        <Stack spacing={3}>
          {!savedModel && <Stepper activeStep={step} alternativeLabel><Step><StepLabel>Informações</StepLabel></Step><Step><StepLabel>Unidades e revisão</StepLabel></Step></Stepper>}
          {error && <Alert severity="error">{error}</Alert>}
          {step === 0 || savedModel ? <>
            <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', md: 'minmax(0, 1fr) 260px' }, gap: 3 }}>
              <Stack spacing={2}>
                <Typography variant="h4" component="h3">No catálogo</Typography>
                {field('name', 'Nome do equipamento', 200, true)}
                <TextField label="Descrição" multiline minRows={3} fullWidth value={form.description} disabled={busy} onChange={(event) => change('description', event.target.value)} error={!!errors.description} helperText={errors.description || 'Estas informações e a foto aparecem para clientes e visitantes.'} slotProps={{ htmlInput: { maxLength: 4000 } }} />
              </Stack>
              <Stack spacing={1.5} sx={{ minWidth: 0 }}>
                <Typography variant="h4" component="h3">Foto do equipamento</Typography>
                <Box sx={{ borderRadius: 2, overflow: 'hidden', border: '1px solid', borderColor: 'divider' }}><EquipmentPhoto url={photoUrl} name={form.name || 'equipamento'} token={token} /></Box>
                <Tabs value={photoMode} onChange={(_, value) => { if (!busy) { dirty.current = true; setPhotoMode(value) } }} aria-label="Origem da foto" variant="fullWidth"><Tab value="upload" label="Enviar foto" disabled={busy} /><Tab value="link" label="Usar link" disabled={busy} /></Tabs>
                {photoMode === 'upload' ? <>
                  <Button component="label" variant="outlined" disabled={busy} sx={{ position: 'relative' }}>Escolher foto<input aria-label="Escolher foto do equipamento" type="file" accept="image/jpeg,image/png,image/webp" disabled={busy} style={{ position: 'absolute', inset: 0, opacity: 0, width: '100%', cursor: 'pointer' }} onChange={(event) => { const chosen = event.target.files?.[0]; event.target.value = ''; if (!chosen) return; if (chosen.size > 5 * 1024 * 1024 || !['image/jpeg', 'image/png', 'image/webp'].includes(chosen.type)) { setErrors((old) => ({ ...old, photo: 'Escolha JPEG, PNG ou WebP de até 5 MB.' })); return } dirty.current = true; setFile(chosen); setRemovedPhoto(false); setErrors((old) => ({ ...old, photo: '' })) }} /></Button>
                  <Typography variant="caption" color={errors.photo ? 'error' : 'text.secondary'} sx={{ overflowWrap: 'anywhere' }}>{errors.photo || file?.name || 'JPEG, PNG ou WebP · até 5 MB'}</Typography>
                  {(file || model?.image_source === 'upload') && !removedPhoto && <Button disabled={busy} onClick={() => { dirty.current = true; setFile(null); setRemovedPhoto(true) }}>Remover foto</Button>}
                </> : field('image_url', 'Link da imagem', 2048)}
              </Stack>
            </Box>
            <Divider />
            <Stack spacing={2}><Box><Typography variant="h4" component="h3">Detalhes internos</Typography><Typography color="text.secondary" variant="body2">Opcionais e visíveis apenas para administradores.</Typography></Box>
              <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', sm: '1fr 1fr' }, gap: 2 }}>{field('brand', 'Marca', 100)}{field('manufacturer_model', 'Modelo do fabricante', 100)}</Box>
              {field('category', 'Categoria', 80)}
            </Stack>
          </> : <>
            <Box><Typography component="h3" variant="h3">{form.name}</Typography><Typography color="text.secondary">Quantas unidades físicas deste equipamento existem na academia?</Typography></Box>
            <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2}>
              <TextField label="Quantidade inicial" type="number" required fullWidth value={form.initial_quantity} onChange={(event) => change('initial_quantity', event.target.value)} error={!!errors.initial_quantity} helperText={errors.initial_quantity || 'De 1 a 100 unidades por cadastro.'} slotProps={{ htmlInput: { min: 1, max: 100, step: 1 } }} disabled={busy} />
              {field('unit_prefix', 'Prefixo dos identificadores', 40)}
            </Stack>
            <Box sx={{ bgcolor: 'action.hover', p: 2, borderRadius: 2 }}><Typography variant="overline" color="primary">Identificação automática</Typography><Typography sx={{ overflowWrap: 'anywhere' }}>{form.unit_prefix.trim() || 'UN'}-01{Number(form.initial_quantity) > 1 ? ` até ${form.unit_prefix.trim() || 'UN'}-${String(form.initial_quantity).padStart(2, '0')}` : ''}</Typography><Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>Cada unidade será cadastrada como ativa e em funcionamento. Você poderá editar seus detalhes após salvar.</Typography></Box>
          </>}
        </Stack>
      </DialogContent>
      <DialogActions sx={{ px: 3, py: 2, flexWrap: 'wrap', gap: 1 }}>
        <Button disabled={busy} onClick={close}>Cancelar</Button>
        {!savedModel && step === 1 && <Button disabled={busy} onClick={() => setStep(0)}>Voltar</Button>}
        {!savedModel && step === 0 ? <Button variant="contained" onClick={() => { if (validate()) setStep(1) }}>Continuar</Button> : <Button disabled={busy} variant="contained" onClick={() => void save()}>{busy ? 'Salvando...' : savedModel ? 'Salvar alterações' : 'Cadastrar equipamento'}</Button>}
      </DialogActions>
    </Dialog>
    <Dialog open={discard} onClose={() => setDiscard(false)} aria-labelledby="equipment-discard-title"><DialogTitle id="equipment-discard-title">Descartar alterações?</DialogTitle><DialogContent>Os dados que ainda não foram salvos serão perdidos.</DialogContent><DialogActions><Button autoFocus onClick={() => setDiscard(false)}>Continuar editando</Button><Button onClick={onClose}>Descartar</Button></DialogActions></Dialog>
  </>
}
