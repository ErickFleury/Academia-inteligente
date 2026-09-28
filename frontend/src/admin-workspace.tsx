import { Box, Stack, Tab, Tabs } from '@mui/material'
import { useState } from 'react'
import { AdminDashboard } from './admin-dashboard-page'
import { ClientManagement } from './client-management'
import { EmployeeManagement } from './employee-management'
import { PageHeader } from './components/ui'

export function AdminWorkspace({ accessToken, onUnauthenticated }: { accessToken: string; onUnauthenticated: () => void }) {
  const [tab, setTab] = useState('overview')
  return <Stack spacing={3} sx={{ minWidth: 0 }}>
    <PageHeader eyebrow="Operação" title="Painel administrativo" description="Acompanhe a academia e encontre os cadastros em um só lugar." />
    <Tabs value={tab} onChange={(_, value: string) => setTab(value)} variant="fullWidth" aria-label="Seções do painel administrativo">
      <Tab id="admin-tab-overview" aria-controls="admin-panel-overview" value="overview" label="Visão geral" />
      <Tab id="admin-tab-clients" aria-controls="admin-panel-clients" value="clients" label="Clientes" />
      <Tab id="admin-tab-employees" aria-controls="admin-panel-employees" value="employees" label="Instrutores" />
    </Tabs>
    {/* Keep existing data and local drafts while moving between sections. */}
    <Box role="tabpanel" id="admin-panel-overview" aria-labelledby="admin-tab-overview" hidden={tab !== 'overview'}>
      <AdminDashboard accessToken={accessToken} onUnauthenticated={onUnauthenticated} />
    </Box>
    <Box role="tabpanel" id="admin-panel-clients" aria-labelledby="admin-tab-clients" hidden={tab !== 'clients'}>
      <ClientManagement accessToken={accessToken} onUnauthenticated={onUnauthenticated} />
    </Box>
    <Box role="tabpanel" id="admin-panel-employees" aria-labelledby="admin-tab-employees" hidden={tab !== 'employees'}>
      <EmployeeManagement accessToken={accessToken} onUnauthenticated={onUnauthenticated} />
    </Box>
  </Stack>
}
