import { Alert, Box, Button, Card, CardContent, Stack, Typography } from '@mui/material'
import { useEffect, useRef, useState } from 'react'
import { BrowserRouter, Navigate, useLocation, useNavigate } from 'react-router-dom'

import { AdminShell, ClientNavigationStateProvider, ClientShell, PublicShell } from './components/application-shell'
import { RouterButtonLink } from './components/router-button-link'
import { LoadingState, PageHeader, StatusNotice } from './components/ui'
import { OidcSessionClient, sessionIdleTimeoutMs, type Session } from './auth'
import { ClientManagement } from './client-management'
import { AdminDashboard } from './admin-dashboard-page'
import { OnboardingAccessPage } from './onboarding-access-page'
import { OnboardingConversationPage } from './onboarding-conversation-page'
import { OnboardingForm } from './onboarding-form'
import { getOwnOnboardingDraft } from './onboarding-draft'
import { CurrentTrainingPage } from './current-training-page'
import { TrainingChatPage } from './training-chat-page'
import { InstructorAdaptationsPage } from './instructor-adaptations-page'
import { ProgressPage } from './progress-page'
import { ProgressModerationPage } from './progress-moderation-page'
import { EquipmentCatalogPage } from './equipment-catalog-page'
import { EquipmentManagementPage } from './equipment-management-page'
import { OccupancyPage } from './occupancy-page'
import { SocialProfilePage } from './social-profile-page'
import { PostDetailPage } from './post-detail-page'

const oidcSessionClient = new OidcSessionClient()

export function App() {
  return <BrowserRouter><Application /></BrowserRouter>
}

function Application() {
  const location = useLocation()
  const navigate = useNavigate()
  const isEquipmentCatalogRoute = location.pathname === '/equipamentos'
  const [session, setSession] = useState<Session | null>(() => oidcSessionClient.getSession())
  const [completingLogin, setCompletingLogin] = useState(false)
  const [authenticationError, setAuthenticationError] = useState<string | null>(null)
  const [loggedOut, setLoggedOut] = useState(() => oidcSessionClient.hasLoggedOut())
  const [onboardingComplete, setOnboardingComplete] = useState<boolean | null>(null)
  const loginCompletionStarted = useRef(false)
  const loginRedirectStarted = useRef(false)
  const logoutStarted = useRef(false)

  useEffect(() => {
    if (!new URL(window.location.href).searchParams.has('code') || loginCompletionStarted.current) return
    loginCompletionStarted.current = true
    setCompletingLogin(true)
    void oidcSessionClient
      .completeLogin()
      .then((returnPath) => {
        setSession(oidcSessionClient.getSession())
        navigate(returnPath, { replace: true })
      })
      .catch(() => setAuthenticationError('Não foi possível iniciar a sessão. Tente novamente.'))
      .finally(() => setCompletingLogin(false))
  }, [navigate])

  useEffect(() => {
    if (!session?.roles.includes('client')) {
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
      || isEquipmentCatalogRoute
      || new URL(window.location.href).searchParams.has('code')
      || loggedOut
      || loginRedirectStarted.current
    ) return
    loginRedirectStarted.current = true
    void oidcSessionClient.startLogin().catch(() => {
      loginRedirectStarted.current = false
      setAuthenticationError('Não foi possível abrir o login. Tente novamente.')
    })
  }, [authenticationError, completingLogin, loggedOut, session])

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
      oidcSessionClient.recordActivity()
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

  const isAdministrator = session?.roles.includes('admin') ?? false
  const isAdministrativeRoute = location.pathname === '/admin'
    || (isAdministrator && (location.pathname === '/' || location.pathname === '/dashboard'))
  const isProgressModerationRoute = location.pathname === '/admin/publicacoes'
  const isOnboardingRoute = location.pathname === '/onboarding'
  const isOnboardingConversationRoute = location.pathname === '/onboarding/conversa'
  const isCurrentTrainingRoute = location.pathname === '/treino'
  const isTrainingChatRoute = location.pathname === '/assistente'
  const isProgressRoute = location.pathname === '/feed'
  const isEquipmentManagementRoute = location.pathname === '/admin/equipamentos'
  const isOccupancyRoute = location.pathname === '/ocupacao'
  const isProfileRoute = location.pathname === '/perfil'
  const viewedProfileId = location.pathname.match(/^\/perfis\/([^/]+)$/)?.[1]
  const viewedPostId = location.pathname.match(/^\/publicacoes\/([^/]+)$/)?.[1]
  const isInstructorAdaptationsRoute = location.pathname === '/instrutor/adaptacoes'
  const isClientOnboardingRoute = isOnboardingRoute || isOnboardingConversationRoute
  const isClientRoute = isClientOnboardingRoute || isCurrentTrainingRoute || isTrainingChatRoute || isProgressRoute || isOccupancyRoute || isProfileRoute || Boolean(viewedProfileId) || Boolean(viewedPostId)
  const isInstructor = session?.roles.includes('instructor') ?? false

  function clearSession() {
    oidcSessionClient.clearSession()
    setSession(null)
  }

  async function endSession() {
    if (logoutStarted.current) return
    logoutStarted.current = true
    const logoutUrl = await oidcSessionClient.endSession()
    setSession(null)
    setLoggedOut(true)
    window.location.assign(logoutUrl)
  }

  const onboardingToken = new URLSearchParams(location.search).get('token')

  if (isOnboardingRoute && onboardingToken) {
    return <OnboardingAccessPage token={onboardingToken} />
  }

  if (isEquipmentCatalogRoute) {
    if (session?.roles.includes('client')) {
      return <ClientNavigationStateProvider onboardingComplete={onboardingComplete}><EquipmentCatalogPage onSignOut={endSession} showClientNavigation /></ClientNavigationStateProvider>
    }
    return <EquipmentCatalogPage />
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
    if (loggedOut) {
      return (
        <PublicShell>
          <Stack spacing={3} sx={{ maxWidth: 520, py: { xs: 2, sm: 5 } }}>
            <Typography component="h1" variant="h2">Sessão encerrada</Typography>
            <Typography color="text.secondary">Você saiu da sua conta com segurança.</Typography>
            <Box><Button onClick={() => { oidcSessionClient.beginLoginAfterLogout(); setLoggedOut(false); loginRedirectStarted.current = false }} variant="contained">Entrar novamente</Button></Box>
          </Stack>
        </PublicShell>
      )
    }
    return <PublicShell><LoadingState label="Redirecionando para o login" /></PublicShell>
  }

  if (isClientRoute && !session?.roles.includes('client')) {
    return (
      <ClientNavigationStateProvider onboardingComplete={onboardingComplete}>
        <ClientShell onSignOut={endSession} showClientNavigation={session.roles.includes('client')}>
          <PageHeader eyebrow="Acesso protegido" title="Área do cliente indisponível" />
          <Alert severity="error" variant="outlined">Você não tem permissão para acessar esta área.</Alert>
        </ClientShell>
      </ClientNavigationStateProvider>
    )
  }

  if (isInstructorAdaptationsRoute && !isInstructor) {
    return (
      <ClientNavigationStateProvider onboardingComplete={onboardingComplete}>
        <ClientShell onSignOut={endSession} showClientNavigation={session.roles.includes('client')}>
          <PageHeader eyebrow="Acesso protegido" title="Área do instrutor indisponível" />
          <Alert severity="error" variant="outlined">Você não tem permissão para acessar esta página.</Alert>
        </ClientShell>
      </ClientNavigationStateProvider>
    )
  }

  if (isInstructorAdaptationsRoute && session) {
    return <InstructorAdaptationsPage accessToken={session.accessToken} onSignOut={endSession} />
  }

  if (isOnboardingConversationRoute && session) {
    return <Navigate replace to="/assistente" />
  }

  if (isOnboardingRoute && session) {
    return <ClientNavigationStateProvider onboardingComplete={onboardingComplete}><OnboardingForm accessToken={session.accessToken} onCompleted={() => setOnboardingComplete(true)} onSignOut={endSession} /></ClientNavigationStateProvider>
  }

  if (isCurrentTrainingRoute && session) {
    return <ClientNavigationStateProvider onboardingComplete={onboardingComplete}><CurrentTrainingPage accessToken={session.accessToken} onSignOut={endSession} /></ClientNavigationStateProvider>
  }

  if (isTrainingChatRoute && session) {
    return (
      <ClientNavigationStateProvider onboardingComplete={onboardingComplete}>
        {onboardingComplete === null
          ? <ClientShell onSignOut={endSession} showClientNavigation><LoadingState label="Preparando seu assistente" /></ClientShell>
          : onboardingComplete
            ? <TrainingChatPage accessToken={session.accessToken} onSignOut={endSession} />
            : <OnboardingConversationPage accessToken={session.accessToken} onSignOut={endSession} />}
      </ClientNavigationStateProvider>
    )
  }

  if (isProgressRoute && session) {
    return <ClientNavigationStateProvider onboardingComplete={onboardingComplete}><ProgressPage accessToken={session.accessToken} onSignOut={endSession} /></ClientNavigationStateProvider>
  }

  if (isOccupancyRoute && session) {
    return <ClientNavigationStateProvider onboardingComplete={onboardingComplete}><OccupancyPage onSignOut={endSession} /></ClientNavigationStateProvider>
  }

  if (isProfileRoute && session) {
    return <ClientNavigationStateProvider onboardingComplete={onboardingComplete}><SocialProfilePage accessToken={session.accessToken} onSignOut={endSession} /></ClientNavigationStateProvider>
  }

  if (viewedProfileId && session) {
    return <ClientNavigationStateProvider onboardingComplete={onboardingComplete}><SocialProfilePage accessToken={session.accessToken} onSignOut={endSession} profileId={viewedProfileId} /></ClientNavigationStateProvider>
  }

  if (viewedPostId && session) {
    return <ClientNavigationStateProvider onboardingComplete={onboardingComplete}><PostDetailPage accessToken={session.accessToken} onSignOut={endSession} postId={viewedPostId} /></ClientNavigationStateProvider>
  }

  if ((isAdministrativeRoute || isProgressModerationRoute || isEquipmentManagementRoute) && !isAdministrator) {
    return (
      <ClientNavigationStateProvider onboardingComplete={onboardingComplete}>
        <ClientShell onSignOut={endSession} showClientNavigation={session.roles.includes('client')}>
          <PageHeader eyebrow="Acesso protegido" title="Área restrita" />
          <Alert severity="error" variant="outlined">Você não tem permissão para acessar esta página.</Alert>
        </ClientShell>
      </ClientNavigationStateProvider>
    )
  }

  if (isProgressModerationRoute && session) {
    return <ProgressModerationPage accessToken={session.accessToken} onSignOut={endSession} />
  }

  if (isEquipmentManagementRoute && session) {
    return <EquipmentManagementPage accessToken={session.accessToken} onSignOut={endSession} />
  }

  if (isAdministrativeRoute && session) {
    return (
      <AdminShell onSignOut={endSession}>
        <Stack spacing={3}>
          <PageHeader
            action={<Stack direction={{ xs: 'column', sm: 'row' }} spacing={1}><RouterButtonLink to="/admin/equipamentos" variant="outlined">Gerenciar equipamentos</RouterButtonLink><RouterButtonLink to="/admin/publicacoes" variant="outlined">Moderar publicações</RouterButtonLink></Stack>}
            description="Acompanhe indicadores agregados e gerencie os clientes da academia."
            eyebrow="Operação"
            title="Painel administrativo"
          />
          <AdminDashboard accessToken={session.accessToken} onUnauthenticated={clearSession} />
          <ClientManagement accessToken={session.accessToken} onUnauthenticated={clearSession} />
        </Stack>
      </AdminShell>
    )
  }

  if (session) {
    return (
      <ClientNavigationStateProvider onboardingComplete={onboardingComplete}>
      <ClientShell onSignOut={endSession} showClientNavigation={!isAdministrator && session.roles.includes('client')}>
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
                    {onboardingComplete === false && <RouterButtonLink to="/onboarding" variant="contained">Preencher onboarding</RouterButtonLink>}
                    <RouterButtonLink to="/treino" variant="outlined">Ver meu treino</RouterButtonLink>
                    <RouterButtonLink to="/assistente" variant="outlined">Assistente de treino</RouterButtonLink>
                  </Stack>
                )}
                {isAdministrator && <Box><RouterButtonLink to="/admin" variant="contained">Administração</RouterButtonLink></Box>}
              </Stack>
            </CardContent>
          </Card>
        </Stack>
      </ClientShell>
      </ClientNavigationStateProvider>
    )
  }

  return null
}
