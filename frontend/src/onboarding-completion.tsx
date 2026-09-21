import { Button, Card, CardContent, Stack, Typography } from '@mui/material'

import { StatusNotice } from './components/ui'

type OnboardingCompletionProps = {
  completedAt: string | null
  missingFields: string[]
  onComplete: () => void
  submitting: boolean
}

const labels: Record<string, string> = {
  training_goal: 'objetivo de treino',
  training_experience: 'experiência de treino',
  height_cm: 'altura',
  weight_kg: 'peso',
  has_limitations_or_complaints: 'resposta sobre limitações ou queixas',
  limitations_or_complaints: 'detalhes de limitações ou queixas',
  uses_medications: 'resposta sobre medicações',
  medications: 'detalhes de medicações',
  has_health_conditions: 'resposta sobre condições de saúde',
  health_conditions: 'detalhes de condições de saúde',
}

export function OnboardingCompletion({ completedAt, missingFields, onComplete, submitting }: OnboardingCompletionProps) {
  if (completedAt) {
    return <StatusNotice severity="success">Onboarding concluído em {new Intl.DateTimeFormat('pt-BR', { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(completedAt))}. Seus dados não podem mais ser alterados por aqui.</StatusNotice>
  }
  const missing = missingFields.map((field) => labels[field] ?? field)
  return (
    <Card component="section">
      <CardContent>
        <Stack spacing={1.5}>
          <Typography component="h2" variant="h3">Revisar e concluir</Typography>
          {missing.length > 0 ? <StatusNotice severity="info">Antes de concluir, complete: {missing.join(', ')}.</StatusNotice> : <StatusNotice severity="success">Tudo pronto para concluir seu onboarding.</StatusNotice>}
          <Button disabled={missing.length > 0 || submitting} onClick={onComplete} variant="contained">
            {submitting ? 'Concluindo…' : 'Concluir onboarding'}
          </Button>
        </Stack>
      </CardContent>
    </Card>
  )
}
