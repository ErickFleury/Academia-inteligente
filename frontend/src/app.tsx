import { Alert, Box, Button, Card, CardContent, Stack, Typography } from '@mui/material'
import { useEffect, useRef, useState } from 'react'

import { AdminShell, ClientShell, PublicShell } from './components/application-shell'
import { LoadingState, PageHeader, StatusNotice } from './components/ui'
import { OidcSessionClient, sessionIdleTimeoutMs, type Session } from './auth'
import { ClientManagement } from './client-management'
import { OnboardingAccessPage } from './onboarding-access-page'
import { OnboardingConversationPage } from './onboarding-conversation-page'
import { OnboardingForm } from './onboarding-form'
import { getOwnOnboardingDraft } from './onboarding-draft'
import { CurrentTrainingPage } from './current-training-page'
import { TrainingChatPage } from './training-chat-page'

const oidcSessionClient = new OidcSessionClient()

export function App() {
  const [session, setSession] = useState<Session | null>(() => oidcSessionClient.getSession())
  const [completingLogin, setCompletingLogin] = useState(false)
  const [authenticationError, setAuthenticationError] = useState<string | null>(null)
  const [onboardingComplete, setOnboardingComplete] = useState<boolean | null>(null)
  const loginCompletionStarted = useRef(false)
  const loginRedirectStarted = useRef(false)

  useEffect(() => {
    if (!new URL(window.location.href).searchParams.has('code') || loginCompletionStarted.current) return
    loginCompletionStarted.current = true
    setCompletingLogin(true)
    void oidcSessionClient
      .completeLogin()
      .then(() => setSession(oidcSessionClient.getSession()))
      .catch(() => setAuthenticationError('Não foi possível iniciar a sessão. Tente novamente.'))
      .finally(() => setCompletingLogin(false))
  }, [])

  useEffect(() => {
    const isClientHome = window.location.pathname === '/' || window.location.pathname === '/dashboard'
    if (!session?.roles.includes('client') || !isClientHome) {
      setOnboardingComplete(null)
      return
    }
    let active = true
    setOnboardingComplete(null)
    void getOwnOnboardingDraft(session.accessToken)
      .then((draft) => active && setOnboardingComplete(draft.status === 'completed'))
      .catch(() => active && setOnboardingComplete(null))
    return () => { active = false }
  }, [session])

  useEffect(() => {
    if (
      session
      || completingLogin
      || authenticationError
      || new URL(window.location.href).searchParams.has('code')
      || loginRedirectStarted.current
    ) return
    loginRedirectStarted.current = true
    void oidcSessionClient.startLogin().catch(() => {
      loginRedirectStarted.current = false
      setAuthenticationError('Não foi possível abrir o login. Tente novamente.')
    })
  }, [authenticationError, completingLogin, session])

  useEffect(() => {
    let refreshing = false
    let lastRecordedActivity = 0
    const refreshIfNeeded = async () => {
      const current = oidcSessionClient.getSession()
      if (!current) {
        setSession(null)
        return
      }
      if (current.expiresAt - Date.now() > 60_000 || refreshing) return
      refreshing = true
      try {
        setSession(await oidcSessionClient.refreshSession())
      } finally {
        refreshing = false
      }
    }
    const recordActivity = () => {
      if (Date.now() - lastRecordedActivity < 1_000) return
      lastRecordedActivity = Date.now()
      const current = oidcSessionClient.recordActivity()
      if (current) setSession(current)
      void refreshIfNeeded()
    }
    const activityEvents = ['pointerdown', 'keydown', 'touchstart', 'scroll'] as const
    activityEvents.forEach((event) => window.addEventListener(event, recordActivity, { passive: true }))
    const timer = window.setInterval(() => {
      const current = oidcSessionClient.getSession()
      if (!current) {
        setSession(null)
        return
      }
      if (Date.now() - current.lastActivityAt >= sessionIdleTimeoutMs) {
        clearSession()
        return
      }
      void refreshIfNeeded()
    }, 1_000)
    return () => {
      activityEvents.forEach((event) => window.removeEventListener(event, recordActivity))
      window.clearInterval(timer)
    }
  }, [])

  const isAdministrativeRoute = window.location.pathname === '/admin'
  const isOnboardingRoute = window.location.pathname === '/onboarding'
  const isOnboardingConversationRoute = window.location.pathname === '/onboarding/conversa'
  const isCurrentTrainingRoute = window.location.pathname === '/treino'
  const isTrainingChatRoute = window.location.pathname === '/assistente'
  const isClientOnboardingRoute = isOnboardingRoute || isOnboardingConversationRoute
  const isClientRoute = isClientOnboardingRoute || isCurrentTrainingRoute || isTrainingChatRoute
  const isAdministrator = session?.roles.includes('admin') ?? false

  function clearSession() {
    oidcSessionClient.clearSession()
    setSession(null)
  }

  function endSession() {
    const logoutUrl = oidcSessionClient.endSession()
    setSession(null)
    window.location.assign(logoutUrl)
  }

  const onboardingToken = new URL(window.location.href).searchParams.get('token')

  if (isOnboardingRoute && onboardingToken) {
    return <OnboardingAccessPage token={onboardingToken} />
  }

  if (completingLogin) return <PublicShell><LoadingState label="Iniciando sessão" /></PublicShell>

  if (authenticationError) {
    return (
      <PublicShell>
        <Stack spacing={3} sx={{ maxWidth: 650, py: { xs: 2, sm: 5 } }}>
          <Typography component="h1" variant="h2">Não foi possível entrar</Typography>
          <Alert severity="error" variant="outlined">{authenticationError}</Alert>
          <Box><Button onClick={() => setAuthenticationError(null)} variant="contained">Tentar novamente</Button></Box>
        </Stack>
      </PublicShell>
    )
  }

  if (!session) {
    return <PublicShell><LoadingState label="Redirecionando para o login" /></PublicShell>
  }

  if (isClientRoute && !session?.roles.includes('client')) {
    return (
      <ClientShell onSignOut={endSession}>
        <PageHeader eyebrow="Acesso protegido" title="Área do cliente indisponível" />
        <Alert severity="error" variant="outlined">Você não tem permissão para acessar esta área.</Alert>
      </ClientShell>
    )
  }

  if (isOnboardingConversationRoute && session) {
    return <OnboardingConversationPage accessToken={session.accessToken} onSignOut={endSession} />
  }

  if (isOnboardingRoute && session) {
    return <OnboardingForm accessToken={session.accessToken} onSignOut={endSession} />
  }

  if (isCurrentTrainingRoute && session) {
    return <CurrentTrainingPage accessToken={session.accessToken} onSignOut={endSession} />
  }

  if (isTrainingChatRoute && session) {
    return <TrainingChatPage accessToken={session.accessToken} onSignOut={endSession} />
  }

  if (isAdministrativeRoute && !isAdministrator) {
    return (
      <ClientShell onSignOut={endSession}>
        <PageHeader eyebrow="Acesso protegido" title="Área restrita" />
        <Alert severity="error" variant="outlined">Você não tem permissão para acessar esta página.</Alert>
      </ClientShell>
    )
  }

  if (isAdministrativeRoute && session) {
    return (
      <AdminShell onSignOut={endSession}>
        <Stack spacing={3}>
          <PageHeader
            action={<Button component="a" href="/admin" variant="outlined">Administração</Button>}
            description="Cadastre, localize e acompanhe o estado de acesso dos clientes."
            eyebrow="Operação"
            title="Clientes"
          />
          <ClientManagement accessToken={session.accessToken} onUnauthenticated={clearSession} />
        </Stack>
      </AdminShell>
    )
  }

  if (session) {
    return (
      <ClientShell onSignOut={endSession}>
        <Stack spacing={3} sx={{ maxWidth: 760 }}>
          <PageHeader eyebrow="Sessão segura" title="Bem-vindo à Academia Inteligente" />
          <StatusNotice severity="success">Sessão autenticada.</StatusNotice>
          <Card>
            <CardContent>
              <Stack spacing={2}>
                <Typography component="h2" variant="h3">Seu espaço está pronto</Typography>
                <Typography color="text.secondary">Novos recursos pessoais aparecerão aqui conforme forem disponibilizados.</Typography>
                {!isAdministrator && (
                  <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1.25} sx={{ alignItems: { xs: 'stretch', sm: 'center' } }}>
                    {onboardingComplete === false && <Button component="a" href="/onboarding" variant="contained">Preencher onboarding</Button>}
                    <Button component="a" href="/treino" variant="outlined">Ver meu treino</Button>
                    <Button component="a" href="/assistente" variant="outlined">Assistente de treino</Button>
                  </Stack>
                )}
                {isAdministrator && <Box><Button component="a" href="/admin" variant="contained">Administração</Button></Box>}
              </Stack>
            </CardContent>
          </Card>
        </Stack>
      </ClientShell>
    )
  }

  return null
}
