import { Box, Button, Card, CardContent, Chip, Divider, Stack, Typography } from '@mui/material'
import { useEffect, useState } from 'react'

import { ClientShell } from './components/application-shell'
import { EmptyState, LoadingState, PageHeader, StatusNotice } from './components/ui'
import { getCurrentTrainingPlan, type CurrentTrainingPlan } from './training-plan'

type CurrentTrainingPageProps = { accessToken: string; onSignOut: () => void }

function restLabel(restSeconds: number) {
  return restSeconds === 0 ? 'Sem descanso programado' : `Descanso: ${restSeconds} s`
}

export function CurrentTrainingPage({ accessToken, onSignOut }: CurrentTrainingPageProps) {
  const [plan, setPlan] = useState<CurrentTrainingPlan | null | undefined>(undefined)
  const [error, setError] = useState<string | null>(null)

  async function loadPlan() {
    setError(null)
    setPlan(undefined)
    try {
      setPlan(await getCurrentTrainingPlan(accessToken))
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Não foi possível carregar seu treino.')
      setPlan(null)
    }
  }

  useEffect(() => { void loadPlan() }, [accessToken])

  if (plan === undefined) {
    return <ClientShell onSignOut={onSignOut}><LoadingState label="Carregando seu treino" /></ClientShell>
  }

  return (
    <ClientShell onSignOut={onSignOut}>
      <Stack spacing={{ xs: 2.5, sm: 3 }} sx={{ maxWidth: 860, minWidth: 0 }}>
        <PageHeader
          eyebrow="Treino atual"
          title="Meu treino"
          description="Use esta ficha durante o treino. Siga as orientações e ajuste a carga somente com acompanhamento profissional."
        />
        {error && (
          <Stack spacing={1.5} sx={{ alignItems: 'flex-start' }}>
            <StatusNotice severity="error">{error}</StatusNotice>
            <Button onClick={() => void loadPlan()} variant="outlined">Tentar novamente</Button>
          </Stack>
        )}
        {!error && !plan && (
          <EmptyState
            title="Seu treino ainda não está disponível"
            description="Quando um instrutor revisar e ativar sua proposta, seu plano aparecerá aqui."
          />
        )}
        {!error && plan && (
          <Card component="section">
            <CardContent sx={{ p: { xs: 2.25, sm: 3 } }}>
              <Stack spacing={2.5}>
                <Stack spacing={0.75}>
                  <Typography color="primary.main" variant="overline">Plano atual</Typography>
                  <Typography component="h2" variant="h3" sx={{ overflowWrap: 'anywhere' }}>{plan.name}</Typography>
                  <Typography color="text.secondary" sx={{ overflowWrap: 'anywhere' }}>{plan.objective}</Typography>
                </Stack>
                <Divider />
                <Stack divider={<Divider flexItem />} spacing={0}>
                  {plan.items.map((item) => (
                    <Box component="article" key={item.position} sx={{ minWidth: 0, py: { xs: 2.25, sm: 2.5 } }}>
                      <Stack spacing={1.25}>
                        <Typography color="primary.main" variant="overline">Exercício {item.position}</Typography>
                        <Typography component="h3" variant="h4" sx={{ overflowWrap: 'anywhere' }}>{item.exercise_name}</Typography>
                        <Stack direction="row" spacing={0.75} sx={{ flexWrap: 'wrap', rowGap: 0.75 }}>
                          <Chip label={`${item.sets} séries`} size="small" />
                          <Chip label={`${item.repetitions} repetições`} size="small" />
                          <Chip label={restLabel(item.rest_seconds)} size="small" />
                        </Stack>
                        <Box sx={{ borderLeft: '3px solid', borderColor: 'primary.main', pl: 1.5 }}>
                          <Typography color="text.secondary" variant="body2">Orientação de carga</Typography>
                          <Typography sx={{ overflowWrap: 'anywhere' }}>{item.load_guidance}</Typography>
                        </Box>
                      </Stack>
                    </Box>
                  ))}
                </Stack>
              </Stack>
            </CardContent>
          </Card>
        )}
      </Stack>
    </ClientShell>
  )
}
