import { Stack } from '@mui/material'
import { type ReactNode } from 'react'
import { useLocation } from 'react-router-dom'

import { SidebarShell } from './components/application-shell'
import { RouterButtonLink } from './components/router-button-link'

const links = [
  ['Feed', '/instrutor/feed'],
  ['Planos pendentes', '/instrutor/planos-pendentes'],
  ['Meus planos', '/instrutor/meus-planos'],
  ['Todos os planos', '/instrutor/todos-os-planos'],
  ['Clientes', '/instrutor/clientes'],
  ['Equipamentos', '/instrutor/equipamentos'],
  ['Perfil', '/instrutor/perfil'],
] as const

function Navigation({ id, onNavigate }: { id?: string; onNavigate?: () => void }) {
  const { pathname } = useLocation()

  return (
    <Stack component="nav" aria-label="Navegação da área do instrutor" id={id} spacing={0.5}>
      {links.map(([label, to]) => {
        const active = pathname === to
        return (
          <RouterButtonLink
            aria-current={active ? 'page' : undefined}
            color={active ? 'primary' : 'inherit'}
            key={to}
            onClick={onNavigate}
            sx={{ justifyContent: 'flex-start', px: 1.5, py: 1, width: '100%' }}
            to={to}
            variant={active ? 'contained' : 'text'}
          >
            {label}
          </RouterButtonLink>
        )
      })}
    </Stack>
  )
}

export function InstructorShell({ children, onSignOut }: { children: ReactNode; onSignOut: () => void }) {
  return (
    <SidebarShell
      area="instructor"
      contentMaxWidth="md"
      navigationId="navegacao-instrutor-movel"
      onSignOut={onSignOut}
      renderNavigation={(props) => <Navigation {...props} />}
    >
      {children}
    </SidebarShell>
  )
}
