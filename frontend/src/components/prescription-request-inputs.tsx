import { Button, Checkbox, FormControlLabel, MenuItem, Stack, TextField, Typography } from '@mui/material'
import { useState } from 'react'
import { saveRequestInputs, type RequestInputRequirements } from '../training-prescription'
import { StatusNotice } from './ui'

export function PrescriptionRequestInputs({ accessToken, requirements, onSaved }: { accessToken: string; requirements: RequestInputRequirements; onSaved: () => void }) {
  const [values, setValues] = useState<Record<string, string>>({})
  const [days, setDays] = useState<number[]>([])
  const [attested, setAttested] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const writable = requirements.requirements.filter((r) => r.can_provide)
  const missingProfessional = requirements.requirements.some((r) => r.source === 'request' && !r.can_provide && r.value === null)
  async function save(event: React.FormEvent) {
    event.preventDefault()
    if (!attested || busy) return
    const observations = Object.fromEntries(writable.filter((r) => values[r.key] !== undefined || r.key === 'schedule_confirmed' && days.length > 0).map((r) => [r.key, { value: r.key === 'schedule_confirmed' ? true : r.value_type === 'boolean' ? values[r.key] === 'true' : r.value_type === 'number' ? Number(values[r.key]) : values[r.key], ...(r.measurement ?? {}) }]))
    setBusy(true); setError(null)
    try {
      await saveRequestInputs(accessToken, { expected_snapshot_hash: requirements.snapshot_hash, values: observations, ...(days.length > 0 ? { schedule: { occurrences: days.map((day) => ({ occurrence_id: `day-${day}`, session_id: 'session-a', day_index: day })) } } : {}) })
      onSaved()
    } catch (reason) { setError(reason instanceof Error ? reason.message : 'Não foi possível confirmar os dados.') }
    finally { setBusy(false) }
  }
  return <Stack component="form" aria-label="Informações necessárias para o treino" spacing={2} onSubmit={(event) => void save(event)}>
    <Typography component="h2" variant="h4">Informações deste pedido</Typography>
    <Typography>Informe somente observações atuais. O registro vale para este pedido e não altera seu onboarding.</Typography>
    {missingProfessional && <StatusNotice severity="info">Algumas observações precisam ser registradas pelo instrutor. Peça a ele uma avaliação ou a elaboração manual da ficha.</StatusNotice>}
    {error && <StatusNotice severity="error">{error}</StatusNotice>}
    {writable.map((r) => r.key === 'schedule_confirmed' ? <Stack key={r.key} spacing={1} component="fieldset" sx={{ border: '1px solid', borderColor: 'divider', p: 2 }}><Typography component="legend">Programação da sessão A a elaborar</Typography>{['Segunda-feira', 'Terça-feira', 'Quarta-feira', 'Quinta-feira', 'Sexta-feira', 'Sábado', 'Domingo'].map((label, index) => <FormControlLabel key={label} label={label} control={<Checkbox checked={days.includes(index)} disabled={busy} onChange={(_, checked) => setDays((old) => checked ? [...old, index].sort() : old.filter((day) => day !== index))} />} />)}</Stack> : r.value_type === 'boolean' || r.key === 'reported_talk_test' ? <TextField key={r.key} select required label={r.label} value={values[r.key] ?? ''} disabled={busy} onChange={(event) => setValues((old) => ({ ...old, [r.key]: event.target.value }))}>{Object.entries(r.key === 'reported_talk_test' ? { talk_not_sing: 'Consigo conversar, mas não cantar', few_words: 'Consigo falar apenas poucas palavras antes de respirar' } : { true: 'Sim', false: 'Não' }).map(([value, label]) => <MenuItem key={value} value={value}>{label}</MenuItem>)}</TextField> : <TextField key={r.key} required label={r.label} type={r.value_type === 'number' ? 'number' : 'text'} value={values[r.key] ?? ''} disabled={busy} onChange={(event) => setValues((old) => ({ ...old, [r.key]: event.target.value }))} />)}
    {writable.length > 0 && <><FormControlLabel label="Confirmo que informei dados observados ou escolhidos por mim para este pedido" control={<Checkbox checked={attested} disabled={busy} onChange={(_, checked) => setAttested(checked)} />} /><Button type="submit" variant="contained" disabled={busy || !attested || writable.some((r) => r.key === 'schedule_confirmed' ? days.length === 0 : !values[r.key])}>Registrar informações</Button></>}
  </Stack>
}
