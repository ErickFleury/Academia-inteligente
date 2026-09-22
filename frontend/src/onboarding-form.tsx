import {
  Box,
  Button,
  Card,
  CardContent,
  FormControl,
  FormHelperText,
  InputLabel,
  MenuItem,
  Select,
  Stack,
  TextField,
  Typography,
} from '@mui/material'
import { useEffect, useState } from 'react'
import type { ReactNode } from 'react'

import { ClientShell } from './components/application-shell'
import { LoadingState, PageHeader, StatusNotice } from './components/ui'
import { OnboardingCompletion } from './onboarding-completion'
import {
  completeOwnOnboarding,
  getOwnOnboardingDraft,
  saveOwnOnboardingDraft,
  type OnboardingDraft,
  type OnboardingDraftUpdate,
  type TrainingExperience,
} from './onboarding-draft'

type OnboardingFormProps = { accessToken: string; onSignOut: () => void }

type FormValues = Omit<OnboardingDraft, 'status' | 'completed_at'>

const emptyValues: FormValues = {
  training_goal: null,
  training_experience: null,
  height_cm: null,
  weight_kg: null,
  has_limitations_or_complaints: null,
  limitations_or_complaints: null,
  uses_medications: null,
  medications: null,
  has_health_conditions: null,
  health_conditions: null,
}

function valuesFromDraft(draft: OnboardingDraft): FormValues {
  const { status: _status, completed_at: _completedAt, ...values } = draft
  return values
}

function missingFields(values: FormValues): string[] {
  const required = ['training_goal', 'training_experience', 'height_cm', 'weight_kg'] as const
  const missing = required.filter((field) => values[field] === null || values[field] === '') as string[]
  if (values.has_limitations_or_complaints === null) missing.push('has_limitations_or_complaints')
  else if (values.has_limitations_or_complaints && !optionalText(values.limitations_or_complaints)) missing.push('limitations_or_complaints')
  if (values.uses_medications === null) missing.push('uses_medications')
  else if (values.uses_medications && !optionalText(values.medications)) missing.push('medications')
  if (values.has_health_conditions === null) missing.push('has_health_conditions')
  else if (values.has_health_conditions && !optionalText(values.health_conditions)) missing.push('health_conditions')
  return missing
}

function optionalText(value: string | null): string | null {
  const normalized = value?.trim() ?? ''
  return normalized || null
}

function optionalNumber(value: string): number | null {
  return value === '' ? null : Number(value)
}

function integerInput(value: string): string | null {
  return /^\d*$/.test(value) ? value : null
}

function decimalInput(value: string): string | null {
  return /^\d*(?:[.,]\d{0,2})?$/.test(value) ? value : null
}

function booleanFromSelect(value: string): boolean | null {
  if (value === 'true') return true
  if (value === 'false') return false
  return null
}

function BooleanSelect({
  id,
  label,
  value,
  onChange,
  disabled = false,
}: {
  id: string
  label: string
  value: boolean | null
  onChange: (value: boolean | null) => void
  disabled?: boolean
}) {
  return (
    <FormControl fullWidth>
      <InputLabel id={`${id}-label`}>{label}</InputLabel>
      <Select
        id={id}
        disabled={disabled}
        label={label}
        labelId={`${id}-label`}
        onChange={(event) => onChange(booleanFromSelect(event.target.value))}
        value={value === null ? '' : String(value)}
      >
        <MenuItem value=""><em>Selecione</em></MenuItem>
        <MenuItem value="false">Não</MenuItem>
        <MenuItem value="true">Sim</MenuItem>
      </Select>
      <FormHelperText>Necessário para concluir</FormHelperText>
    </FormControl>
  )
}

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <Card component="section">
      <CardContent>
        <Stack spacing={2.5}>
          <Typography component="h2" variant="h3">{title}</Typography>
          {children}
        </Stack>
      </CardContent>
    </Card>
  )
}

export function OnboardingForm({ accessToken, onSignOut }: OnboardingFormProps) {
  const [values, setValues] = useState<FormValues>(emptyValues)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [completing, setCompleting] = useState(false)
  const [draft, setDraft] = useState<OnboardingDraft | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)

  useEffect(() => {
    let active = true
    void getOwnOnboardingDraft(accessToken)
      .then((loadedDraft) => {
        if (active) {
          setDraft(loadedDraft)
          setValues(valuesFromDraft(loadedDraft))
        }
      })
      .catch((reason: unknown) => active && setError(reason instanceof Error ? reason.message : 'Não foi possível carregar o onboarding.'))
      .finally(() => active && setLoading(false))
    return () => { active = false }
  }, [accessToken])

  function update<K extends keyof FormValues>(field: K, value: FormValues[K]) {
    setValues((current) => ({ ...current, [field]: value }))
  }

  async function saveDraft() {
    setSaving(true)
    setError(null)
    setSuccess(null)
    const payload: OnboardingDraftUpdate = {
      ...values,
      training_goal: optionalText(values.training_goal),
      height_cm: optionalNumber(values.height_cm === null ? '' : String(values.height_cm)),
      weight_kg:
        optionalText(values.weight_kg === null ? null : String(values.weight_kg))?.replace(',', '.')
        ?? null,
      limitations_or_complaints: optionalText(values.limitations_or_complaints),
      medications: optionalText(values.medications),
      health_conditions: optionalText(values.health_conditions),
    }
    if (payload.has_limitations_or_complaints === false) payload.limitations_or_complaints = null
    if (payload.uses_medications === false) payload.medications = null
    if (payload.has_health_conditions === false) payload.health_conditions = null
    try {
      const saved = await saveOwnOnboardingDraft(accessToken, payload)
      setDraft(saved)
      setValues(valuesFromDraft(saved))
      setSuccess('Rascunho salvo com segurança.')
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Não foi possível salvar seu onboarding.')
    } finally {
      setSaving(false)
    }
  }

  async function complete() {
    setCompleting(true)
    setError(null)
    setSuccess(null)
    try {
      const completed = await completeOwnOnboarding(accessToken)
      setDraft(completed)
      setValues(valuesFromDraft(completed))
      setSuccess('Seu onboarding foi concluído com sucesso.')
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Não foi possível concluir seu onboarding.')
    } finally {
      setCompleting(false)
    }
  }

  if (loading) return <ClientShell onSignOut={onSignOut}><LoadingState label="Carregando seu onboarding" /></ClientShell>

  return (
    <ClientShell onSignOut={onSignOut}>
      <Stack spacing={3} sx={{ maxWidth: 840 }}>
        <PageHeader
          action={<Button component="a" href="/onboarding/conversa" variant="outlined">Responder por conversa</Button>}
          description="Salve seu progresso quando quiser. Os campos marcados como necessários serão validados na conclusão do onboarding."
          eyebrow="Seu perfil de treino"
          title="Conte um pouco sobre você"
        />
        {error && <StatusNotice severity="error">{error}</StatusNotice>}
        {success && <StatusNotice severity="success">{success}</StatusNotice>}
        <Section title="Objetivo e experiência">
          <TextField
            disabled={draft?.status === 'completed'}
            fullWidth
            helperText="Necessário para concluir · até 500 caracteres"
            label="Qual é o seu objetivo de treino?"
            multiline
            onChange={(event) => update('training_goal', event.target.value)}
            value={values.training_goal ?? ''}
          />
          <FormControl fullWidth>
            <InputLabel id="experience-label">Experiência de treino</InputLabel>
            <Select
              disabled={draft?.status === 'completed'}
              label="Experiência de treino"
              labelId="experience-label"
              onChange={(event) => update(
                'training_experience',
                event.target.value ? event.target.value as TrainingExperience : null,
              )}
              value={values.training_experience ?? ''}
            >
              <MenuItem value=""><em>Selecione</em></MenuItem>
              <MenuItem value="none">Nenhuma experiência</MenuItem>
              <MenuItem value="beginner">Iniciante</MenuItem>
              <MenuItem value="intermediate">Intermediário</MenuItem>
              <MenuItem value="advanced">Avançado</MenuItem>
            </Select>
          </FormControl>
        </Section>
        <Section title="Dados físicos">
          <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2}>
            <TextField
              disabled={draft?.status === 'completed'}
              fullWidth
              helperText="Em centímetros · use apenas números · necessário para concluir"
              inputMode="numeric"
              slotProps={{ htmlInput: { maxLength: 3, pattern: '\\d*' } }}
              label="Altura"
              onChange={(event) => {
                const nextValue = integerInput(event.target.value)
                if (nextValue !== null) update('height_cm', optionalNumber(nextValue))
              }}
              type="text"
              value={values.height_cm ?? ''}
            />
            <TextField
              disabled={draft?.status === 'completed'}
              fullWidth
              helperText="Em quilogramas · use apenas números · até 2 casas decimais"
              inputMode="decimal"
              slotProps={{ htmlInput: { maxLength: 6, pattern: '\\d*(?:[.,]\\d{0,2})?' } }}
              label="Peso"
              onChange={(event) => {
                const nextValue = decimalInput(event.target.value)
                if (nextValue !== null) update('weight_kg', nextValue || null)
              }}
              type="text"
              value={values.weight_kg ?? ''}
            />
          </Stack>
        </Section>
        <Section title="Limitações e queixas">
          <BooleanSelect disabled={draft?.status === 'completed'} id="limitations-answer" label="Você tem alguma limitação ou queixa relevante?" onChange={(value) => update('has_limitations_or_complaints', value)} value={values.has_limitations_or_complaints} />
          {values.has_limitations_or_complaints && <TextField disabled={draft?.status === 'completed'} fullWidth helperText="Necessário quando a resposta for sim · até 2.000 caracteres" label="Conte quais são as limitações ou queixas" multiline minRows={4} onChange={(event) => update('limitations_or_complaints', event.target.value)} value={values.limitations_or_complaints ?? ''} />}
        </Section>
        <Section title="Medicações">
          <BooleanSelect disabled={draft?.status === 'completed'} id="medications-answer" label="Você utiliza alguma medicação?" onChange={(value) => update('uses_medications', value)} value={values.uses_medications} />
          {values.uses_medications && <TextField disabled={draft?.status === 'completed'} fullWidth helperText="Necessário quando a resposta for sim · até 2.000 caracteres" label="Quais medicações você utiliza?" multiline minRows={4} onChange={(event) => update('medications', event.target.value)} value={values.medications ?? ''} />}
        </Section>
        <Section title="Condições e histórico de saúde">
          <BooleanSelect disabled={draft?.status === 'completed'} id="health-conditions-answer" label="Você tem alguma condição de saúde ou histórico relevante?" onChange={(value) => update('has_health_conditions', value)} value={values.has_health_conditions} />
          {values.has_health_conditions && <TextField disabled={draft?.status === 'completed'} fullWidth helperText="Necessário quando a resposta for sim · até 2.000 caracteres" label="Conte as condições ou o histórico relevante" multiline minRows={4} onChange={(event) => update('health_conditions', event.target.value)} value={values.health_conditions ?? ''} />}
        </Section>
        {draft?.status !== 'completed' && <Box><Button disabled={saving} onClick={() => void saveDraft()} size="large" variant="contained">{saving ? 'Salvando rascunho…' : 'Salvar rascunho'}</Button></Box>}
        <OnboardingCompletion completedAt={draft?.completed_at ?? null} missingFields={missingFields(values)} onComplete={() => void complete()} submitting={completing} />
      </Stack>
    </ClientShell>
  )
}
