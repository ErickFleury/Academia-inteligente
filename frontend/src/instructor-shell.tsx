import { Stack } from '@mui/material'
import { type ReactNode } from 'react'
import { useLocation } from 'react-router-dom'

import { WorkspaceIcon, navigationLinkSx, type WorkspaceIconName } from './components/workspace-presentation'
import { SidebarShell } from './components/application-shell'
import { RouterButtonLink } from './components/router-button-link'

const icons: WorkspaceIconName[] = ['feed', 'pending', 'training', 'plans', 'clients', 'equipment', 'profile']
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
      {links.map(([label, to], index) => {
        const active = pathname === to
        return (
          <RouterButtonLink
            startIcon={<WorkspaceIcon name={icons[index]} />}
            aria-current={active ? 'page' : undefined}
            color={active ? 'primary' : 'inherit'}
            key={to}
            onClick={onNavigate}
            sx={navigationLinkSx}
            to={to}
            variant="text"
          >
            {label}
          </RouterButtonLink>
        )
      })}
    </Stack>
  )
}

export function InstructorShell({ children, onSignOut, contentMaxWidth = 'md' }: { children: ReactNode; onSignOut: () => void; contentMaxWidth?: 'md' | 'lg' }) {
  return (
    <SidebarShell
      area="instructor"
      contentMaxWidth={contentMaxWidth}
      navigationId="navegacao-instrutor-movel"
      onSignOut={onSignOut}
      renderNavigation={(props) => <Navigation {...props} />}
    >
      {children}
    </SidebarShell>
  )
}
