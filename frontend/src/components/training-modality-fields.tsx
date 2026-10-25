import { MenuItem, Stack, TextField } from '@mui/material'
import type { DoseDetails } from '../training-dose'

export function TrainingModalityFields({ details, index, onChange }: { details: DoseDetails; index: number; onChange: (details: DoseDetails) => void }) {
  const dose = details.dose
  function field(key: string, label: string, integer = false) {
    return <TextField key={key} required fullWidth type="number" label={`${label} ${index + 1}`} value={String(dose[key] ?? '')} slotProps={{ htmlInput: { min: key === 'completed' ? 0 : 0.001, step: integer ? 1 : 'any' } }} onChange={(event) => onChange({ ...details, dose: { ...dose, [key]: integer ? Number(event.target.value) : event.target.value } })} />
  }
  function choice(key: string, label: string, choices: Record<string, string>) {
    return <TextField key={key} select fullWidth label={`${label} ${index + 1}`} value={String(dose[key])} onChange={(event) => onChange({ ...details, dose: { ...dose, [key]: event.target.value } })}>{Object.entries(choices).map(([value, text]) => <MenuItem key={value} value={value}>{text}</MenuItem>)}</TextField>
  }
  return <Stack spacing={1.5}>
    {details.mode === 'aerobic' && <>{field('minutes', 'Duração em minutos')}{choice('intensity', 'Intensidade', { moderate: 'Moderada', vigorous: 'Vigorosa' })}</>}
    {details.mode === 'flexibility' && <>{field('holds', 'Sustentações', true)}{field('hold_seconds', 'Segundos por sustentação')}<TextField required label={`Alvo ${index + 1}`} value={String(dose.target)} onChange={(event) => onChange({ ...details, dose: { ...dose, target: event.target.value } })} /></>}
    {(details.mode === 'balance' || details.mode === 'functional') && <>{field('attempts', 'Tentativas', true)}{field('amount', 'Quantidade por tentativa')}{choice('unit', 'Unidade', { seconds: 'Segundos', steps: 'Passos', repetitions: 'Repetições' })}</>}
    {details.mode !== 'aerobic' && details.mode !== 'resistance' && choice('side', 'Lado', { left: 'Esquerdo', right: 'Direito', each_side: 'Cada lado', bilateral: 'Bilateral' })}
    {details.mode === 'resistance' && <>{field('minimum', 'Repetições ou duração mínima')}{field('maximum', 'Repetições ou duração máxima')}</>}
  </Stack>
}
