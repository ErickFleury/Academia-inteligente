import { AppBar, Box, Button, Container, Stack, Toolbar, Typography } from '@mui/material'
import { createContext, useContext, type ReactNode } from 'react'

type ShellProps = { children: ReactNode; onSignOut?: () => void }

const OnboardingNavigationContext = createContext<boolean | null>(null)

export function ClientNavigationStateProvider({ children, onboardingComplete }: { children: ReactNode; onboardingComplete: boolean | null }) {
  return <OnboardingNavigationContext.Provider value={onboardingComplete}>{children}</OnboardingNavigationContext.Provider>
}

function Brand({ heading = false }: { heading?: boolean }) {
  return (
    <Stack direction="row" spacing={1.25} sx={{ alignItems: 'center' }}>
      <Box aria-hidden="true" sx={{ bgcolor: 'primary.main', borderRadius: 1, height: 18, transform: 'skewX(-18deg)', width: 7 }} />
      <Typography component={heading ? 'h1' : 'span'} sx={{ fontWeight: 850, letterSpacing: '-0.04em' }}>Academia Inteligente</Typography>
    </Stack>
  )
}

function ClientNavigation() {
  const currentPath = window.location.pathname
  const onboardingComplete = useContext(OnboardingNavigationContext)
  const links = [
    { href: '/', label: 'Início' },
    ...(onboardingComplete === false ? [{ href: '/onboarding', label: 'Onboarding' }] : []),
    { href: '/treino', label: 'Meu treino' },
    { href: '/assistente', label: 'Assistente' },
    { href: '/progresso', label: 'Progresso' },
    { href: '/equipamentos', label: 'Equipamentos' },
    { href: '/ocupacao', label: 'Ocupação' },
    { href: '/perfil', label: 'Meu perfil' },
  ]
  return (
    <Box component="nav" aria-label="Navegação da área do cliente" sx={{ borderTop: '1px solid', borderColor: 'divider' }}>
      <Container maxWidth="lg" sx={{ px: { xs: 2, sm: 3 }, py: 1 }}>
        <Stack direction="row" spacing={0.5} sx={{ flexWrap: 'wrap', rowGap: 0.5 }} useFlexGap>
          {links.map((link) => {
            const active = currentPath === link.href || (link.href === '/' && currentPath === '/dashboard')
            return <Button aria-current={active ? 'page' : undefined} color={active ? 'primary' : 'inherit'} component="a" href={link.href} key={link.href} size="small" variant={active ? 'contained' : 'text'}>{link.label}</Button>
          })}
        </Stack>
      </Container>
    </Box>
  )
}

function BaseShell({ children, onSignOut, area, navigation }: ShellProps & { area: string; navigation?: ReactNode }) {
  return (
    <Box sx={{ minHeight: '100vh', background: 'linear-gradient(160deg, #10181B 0%, #162427 52%, #10181B 100%)' }}>
      <AppBar color="transparent" elevation={0} position="sticky" sx={{ backdropFilter: 'blur(14px)', borderBottom: '1px solid', borderColor: 'divider' }}>
        <Toolbar sx={{ gap: 2, minHeight: { xs: 64, sm: 72 }, px: { xs: 2, sm: 3 } }}>
          <Brand />
          <Typography color="text.secondary" sx={{ display: { xs: 'none', sm: 'block' }, fontSize: '0.875rem', ml: 1 }}>{area}</Typography>
          <Box sx={{ flexGrow: 1 }} />
          {onSignOut && <Button color="inherit" onClick={onSignOut}>Sair</Button>}
        </Toolbar>
        {navigation}
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

export function ClientShell({ children, onSignOut, showClientNavigation = false }: ShellProps & { showClientNavigation?: boolean }) {
  return <BaseShell area="Área do cliente" navigation={showClientNavigation ? <ClientNavigation /> : undefined} onSignOut={onSignOut}>{children}</BaseShell>
}
