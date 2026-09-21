import { Alert, Box, Button, Card, CardContent, Stack, Typography } from '@mui/material'
import { useEffect, useRef, useState } from 'react'

import { AdminShell, ClientShell, PublicShell } from './components/application-shell'
import { LoadingState, PageHeader, StatusNotice } from './components/ui'
import { OidcSessionClient, type Session } from './auth'
import { ClientManagement } from './client-management'
import { OnboardingAccessPage } from './onboarding-access-page'

const oidcSessionClient = new OidcSessionClient()

function SignInEntry({ message, onSignIn }: { message?: string; onSignIn: () => void }) {
  return (
    <PublicShell>
      <Stack spacing={3} sx={{ maxWidth: 650, py: { xs: 2, sm: 5 } }}>
        <Typography color="primary.main" variant="overline">Plataforma de gestão e treino</Typography>
        <Typography component="h2" variant="h1">Seu ritmo. Sua evolução.</Typography>
        <Typography color="text.secondary" sx={{ fontSize: { xs: '1rem', sm: '1.125rem' }, maxWidth: 540 }}>
          Acesse sua área ou as operações administrativas com uma sessão segura.
        </Typography>
        {message && <StatusNotice severity="info">{message}</StatusNotice>}
        <Box><Button onClick={onSignIn} size="large" variant="contained">Entrar</Button></Box>
      </Stack>
    </PublicShell>
  )
}

export function App() {
  const [session, setSession] = useState<Session | null>(() => oidcSessionClient.getSession())
  const [completingLogin, setCompletingLogin] = useState(false)
  const [authenticationError, setAuthenticationError] = useState<string | null>(null)
  const loginCompletionStarted = useRef(false)

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

  const isProtectedRoute = window.location.pathname === '/dashboard'
  const isAdministrativeRoute = window.location.pathname === '/admin'
  const isOnboardingRoute = window.location.pathname === '/onboarding'
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

  if (isOnboardingRoute) {
    return <OnboardingAccessPage token={new URL(window.location.href).searchParams.get('token')} />
  }

  if (completingLogin) return <PublicShell><LoadingState label="Iniciando sessão" /></PublicShell>

  if (authenticationError) {
    return (
      <PublicShell>
        <Stack spacing={3} sx={{ maxWidth: 650, py: { xs: 2, sm: 5 } }}>
          <Typography component="h1" variant="h2">Não foi possível entrar</Typography>
          <Alert severity="error" variant="outlined">{authenticationError}</Alert>
          <Box><Button onClick={() => void oidcSessionClient.startLogin()} variant="contained">Tentar novamente</Button></Box>
        </Stack>
      </PublicShell>
    )
  }

  if ((isProtectedRoute || isAdministrativeRoute) && !session) {
    return <SignInEntry message="Sessão necessária para acessar esta página." onSignIn={() => void oidcSessionClient.startLogin()} />
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
                {isAdministrator && <Box><Button component="a" href="/admin" variant="contained">Administração</Button></Box>}
              </Stack>
            </CardContent>
          </Card>
        </Stack>
      </ClientShell>
    )
  }

  return <SignInEntry onSignIn={() => void oidcSessionClient.startLogin()} />
}
