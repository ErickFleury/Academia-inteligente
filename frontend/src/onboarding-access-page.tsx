import { Box, Button, Card, CardContent, Stack, Typography } from '@mui/material'
import { useEffect, useState } from 'react'

import { ClientShell, PublicShell } from './components/application-shell'
import { EmptyState, LoadingState, PageHeader, StatusNotice } from './components/ui'
import {
  redeemOnboardingInvitation,
  type InvitationAccessStatus,
  validateOnboardingInvitation,
} from './onboarding-access'

type OnboardingAccessPageProps = { token: string | null }

export function OnboardingAccessPage({ token }: OnboardingAccessPageProps) {
  const [status, setStatus] = useState<InvitationAccessStatus | 'loading'>(token ? 'loading' : 'invalid')
  const [error, setError] = useState<string | null>(null)
  const [redeeming, setRedeeming] = useState(false)

  useEffect(() => {
    if (!token) return
    let active = true
    void validateOnboardingInvitation(token)
      .then((result) => active && setStatus(result))
      .catch((reason: unknown) => {
        if (!active) return
        setError(reason instanceof Error ? reason.message : 'Não foi possível validar este convite.')
        setStatus('invalid')
      })
    return () => { active = false }
  }, [token])

  async function startOnboarding() {
    if (!token) return
    setRedeeming(true)
    setError(null)
    try {
      setStatus(await redeemOnboardingInvitation(token))
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Não foi possível iniciar o onboarding.')
    } finally {
      setRedeeming(false)
    }
  }

  if (status === 'loading') {
    return <PublicShell><LoadingState label="Validando convite de onboarding" /></PublicShell>
  }

  if (status === 'valid') {
    return (
      <ClientShell>
        <Stack spacing={3} sx={{ maxWidth: 760 }}>
          <PageHeader
            description="Reserve alguns minutos para compartilhar as informações que vão orientar seu treino."
            eyebrow="Primeiro passo"
            title="Seu onboarding começa aqui"
          />
          <Card>
            <CardContent>
              <Stack spacing={2.5}>
                <StatusNotice severity="success">Convite validado. Este acesso é exclusivo para o seu onboarding.</StatusNotice>
                <Typography color="text.secondary">Ao continuar, o convite será usado uma única vez para iniciar este processo.</Typography>
                <Box><Button disabled={redeeming} onClick={() => void startOnboarding()} variant="contained">{redeeming ? 'Iniciando onboarding…' : 'Iniciar onboarding'}</Button></Box>
              </Stack>
            </CardContent>
          </Card>
          {error && <StatusNotice severity="error">{error}</StatusNotice>}
        </Stack>
      </ClientShell>
    )
  }

  if (status === 'redeemed') {
    return (
      <ClientShell>
        <Stack spacing={3} sx={{ maxWidth: 760 }}>
          <PageHeader eyebrow="Acesso confirmado" title="Vamos preparar seu onboarding" />
          <StatusNotice severity="success">Seu convite foi usado com segurança. O formulário será disponibilizado na próxima etapa do onboarding.</StatusNotice>
        </Stack>
      </ClientShell>
    )
  }

  return (
    <PublicShell>
      <Stack spacing={3} sx={{ maxWidth: 700, py: { xs: 2, sm: 5 } }}>
        <PageHeader eyebrow="Convite indisponível" title={status === 'expired' ? 'Este convite expirou' : 'Este convite não está disponível'} />
        {error ? <StatusNotice severity="error">{error}</StatusNotice> : <EmptyState description="Solicite um novo convite à administração da academia." title="Não foi possível abrir o onboarding." />}
      </Stack>
    </PublicShell>
  )
}
