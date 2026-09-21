import { AppBar, Box, Button, Container, Stack, Toolbar, Typography } from '@mui/material'
import type { ReactNode } from 'react'

type ShellProps = { children: ReactNode; onSignOut?: () => void }

function Brand({ heading = false }: { heading?: boolean }) {
  return (
    <Stack direction="row" spacing={1.25} sx={{ alignItems: 'center' }}>
      <Box aria-hidden="true" sx={{ bgcolor: 'primary.main', borderRadius: 1, height: 18, transform: 'skewX(-18deg)', width: 7 }} />
      <Typography component={heading ? 'h1' : 'span'} sx={{ fontWeight: 850, letterSpacing: '-0.04em' }}>Academia Inteligente</Typography>
    </Stack>
  )
}

function BaseShell({ children, onSignOut, area }: ShellProps & { area: string }) {
  return (
    <Box sx={{ minHeight: '100vh', background: 'linear-gradient(160deg, #10181B 0%, #162427 52%, #10181B 100%)' }}>
      <AppBar color="transparent" elevation={0} position="sticky" sx={{ backdropFilter: 'blur(14px)', borderBottom: '1px solid', borderColor: 'divider' }}>
        <Toolbar sx={{ gap: 2, minHeight: { xs: 64, sm: 72 }, px: { xs: 2, sm: 3 } }}>
          <Brand />
          <Typography color="text.secondary" sx={{ display: { xs: 'none', sm: 'block' }, fontSize: '0.875rem', ml: 1 }}>{area}</Typography>
          <Box sx={{ flexGrow: 1 }} />
          {onSignOut && <Button color="inherit" onClick={onSignOut}>Sair</Button>}
        </Toolbar>
      </AppBar>
      <Container component="main" maxWidth="lg" sx={{ py: { xs: 3, sm: 5 } }}>{children}</Container>
    </Box>
  )
}

export function PublicShell({ children }: { children: ReactNode }) {
  return (
    <Box component="main" sx={{ background: 'linear-gradient(145deg, #10181B 0%, #1B2A2E 58%, #10181B 100%)', minHeight: '100vh' }}>
      <Container maxWidth="md" sx={{ py: { xs: 3, sm: 5 } }}>
        <Box component="header" sx={{ mb: { xs: 6, sm: 10 } }}><Brand heading /></Box>
        {children}
      </Container>
    </Box>
  )
}

export function AdminShell({ children, onSignOut }: ShellProps) {
  return <BaseShell area="Administração" onSignOut={onSignOut}>{children}</BaseShell>
}

export function ClientShell({ children, onSignOut }: ShellProps) {
  return <BaseShell area="Área do cliente" onSignOut={onSignOut}>{children}</BaseShell>
}
