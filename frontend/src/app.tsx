import { Alert, Button, CircularProgress, Container, Stack, Typography } from '@mui/material'
import { useEffect, useState } from 'react'

import { OidcSessionClient, type Session } from './auth'

const oidcSessionClient = new OidcSessionClient()

export function App() {
  const [session, setSession] = useState<Session | null>(() => oidcSessionClient.getSession())
  const [completingLogin, setCompletingLogin] = useState(false)
  const [authenticationError, setAuthenticationError] = useState<string | null>(null)

  useEffect(() => {
    if (!new URL(window.location.href).searchParams.has('code')) return
    setCompletingLogin(true)
    void oidcSessionClient
      .completeLogin()
      .then(() => setSession(oidcSessionClient.getSession()))
      .catch(() => setAuthenticationError('Não foi possível iniciar a sessão. Tente novamente.'))
      .finally(() => setCompletingLogin(false))
  }, [])

  const isProtectedRoute = window.location.pathname === '/dashboard'

  return (
    <Container component="main" maxWidth="md" sx={{ py: 4 }}>
      <Stack spacing={2} sx={{ alignItems: 'flex-start' }}>
        <Typography component="h1" variant="h4">
          Academia Inteligente
        </Typography>
        {completingLogin && <CircularProgress aria-label="Iniciando sessão" />}
        {authenticationError && <Alert severity="error">{authenticationError}</Alert>}
        {isProtectedRoute && !session ? (
          <>
            <Alert severity="info">Sessão necessária para acessar esta página.</Alert>
            <Button variant="contained" onClick={() => void oidcSessionClient.startLogin()}>
              Entrar
            </Button>
          </>
        ) : session ? (
          <Alert severity="success">Sessão autenticada.</Alert>
        ) : (
          <Button variant="contained" onClick={() => void oidcSessionClient.startLogin()}>
            Entrar
          </Button>
        )}
      </Stack>
    </Container>
  )
}
