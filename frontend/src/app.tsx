import { Alert, Button, CircularProgress, Container, Stack, Typography } from '@mui/material'
import { useEffect, useRef, useState } from 'react'

import { OidcSessionClient, type Session } from './auth'
import { ClientManagement } from './client-management'

const oidcSessionClient = new OidcSessionClient()

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
  const isAdministrator = session?.roles.includes('admin') ?? false

  function clearSession() {
    oidcSessionClient.clearSession()
    setSession(null)
  }

  return (
    <Container component="main" maxWidth="md" sx={{ py: 4 }}>
      <Stack spacing={2} sx={{ alignItems: 'flex-start' }}>
        <Typography component="h1" variant="h4">
          Academia Inteligente
        </Typography>
        {completingLogin && <CircularProgress aria-label="Iniciando sessão" />}
        {authenticationError && <Alert severity="error">{authenticationError}</Alert>}
        {(isProtectedRoute || isAdministrativeRoute) && !session ? (
          <>
            <Alert severity="info">Sessão necessária para acessar esta página.</Alert>
            <Button variant="contained" onClick={() => void oidcSessionClient.startLogin()}>
              Entrar
            </Button>
          </>
        ) : isAdministrativeRoute && !isAdministrator ? (
          <Alert severity="error">Você não tem permissão para acessar esta página.</Alert>
        ) : session ? (
          <>
            <Alert severity="success">Sessão autenticada.</Alert>
            {isAdministrator && (
              <Button href="/admin" variant="outlined">
                Administração
              </Button>
            )}
            <Button onClick={clearSession} variant="text">
              Sair
            </Button>
            {isAdministrativeRoute && (
              <ClientManagement accessToken={session.accessToken} onUnauthenticated={clearSession} />
            )}
          </>
        ) : (
          <Button variant="contained" onClick={() => void oidcSessionClient.startLogin()}>
            Entrar
          </Button>
        )}
      </Stack>
    </Container>
  )
}
