import { Box, Button, Card, CardContent, Stack, Typography } from '@mui/material'
import { useEffect, useState } from 'react'

import {
  AdminDashboardRequestError,
  getActiveClients,
  getAttendanceHistory,
  getDashboardOccupancy,
  type AttendanceHistory,
  type DashboardOccupancy,
} from './admin-dashboard'
import { WorkspaceIcon } from './components/workspace-presentation'
import { LoadingState, StatusNotice } from './components/ui'

type AdminDashboardProps = {
  accessToken: string
  onUnauthenticated: () => void
}

function formatWeek(weekStart: string): string {
  return new Intl.DateTimeFormat('pt-BR', {
    day: '2-digit', month: '2-digit', timeZone: 'UTC',
  }).format(new Date(`${weekStart}T00:00:00Z`))
}

function errorMessage(reason: unknown): string {
  return reason instanceof Error ? reason.message : 'Não foi possível carregar este indicador.'
}

export function AdminDashboard({ accessToken, onUnauthenticated }: AdminDashboardProps) {
  const [activeClients, setActiveClients] = useState<number | null>(null)
  const [attendance, setAttendance] = useState<AttendanceHistory | null>(null)
  const [occupancy, setOccupancy] = useState<DashboardOccupancy | null>(null)
  const [activeClientsError, setActiveClientsError] = useState<string | null>(null)
  const [attendanceError, setAttendanceError] = useState<string | null>(null)
  const [occupancyError, setOccupancyError] = useState<string | null>(null)

  const handleError = (reason: unknown, setError: (value: string) => void) => {
    if (reason instanceof AdminDashboardRequestError && reason.status === 401) onUnauthenticated()
    setError(errorMessage(reason))
  }

  const loadActiveClients = () => {
    setActiveClients(null); setActiveClientsError(null)
    void getActiveClients(accessToken)
      .then((value) => setActiveClients(value.active_clients))
      .catch((reason: unknown) => handleError(reason, setActiveClientsError))
  }
  const loadAttendance = () => {
    setAttendance(null); setAttendanceError(null)
    void getAttendanceHistory(accessToken)
      .then(setAttendance)
      .catch((reason: unknown) => handleError(reason, setAttendanceError))
  }
  const loadOccupancy = () => {
    setOccupancy(null); setOccupancyError(null)
    void getDashboardOccupancy(accessToken)
      .then(setOccupancy)
      .catch((reason: unknown) => handleError(reason, setOccupancyError))
  }

  useEffect(() => {
    loadActiveClients(); loadAttendance(); loadOccupancy()
  }, [accessToken])

  return <Stack aria-label="Indicadores administrativos" component="section" spacing={2}>
    <Typography component="h2" variant="h3">Indicadores da academia</Typography>
    <Box sx={{ display: 'grid', gap: 2, gridTemplateColumns: { xs: '1fr', sm: 'repeat(2, minmax(0, 1fr))' } }}>
      <Card component="section"><CardContent><Stack spacing={1.5} sx={{ minHeight: 156 }}>
        <Stack direction="row" sx={{ justifyContent: 'space-between', alignItems: 'center', color: 'primary.main' }}><Typography variant="overline">Clientes ativos</Typography><WorkspaceIcon name="clients" /></Stack>
        {activeClientsError ? <IndicatorError message={activeClientsError} onRetry={loadActiveClients} /> : activeClients === null ? <LoadingState label="Carregando clientes ativos" /> : <><Typography component="p" sx={{ color: 'primary.main', fontSize: 'clamp(2.8rem, 5vw, 4rem)', fontWeight: 850, lineHeight: 1 }}>{activeClients}</Typography><Typography color="text.secondary">contas de clientes ativas</Typography></>}
      </Stack></CardContent></Card>
      <Card component="section"><CardContent><Stack spacing={1.5} sx={{ minHeight: 156 }}>
        <Stack direction="row" sx={{ justifyContent: 'space-between', alignItems: 'center', color: 'primary.main' }}><Typography variant="overline">Ocupação atual</Typography><WorkspaceIcon name="profile" /></Stack>
        {occupancyError ? <IndicatorError message={occupancyError} onRetry={loadOccupancy} /> : occupancy === null ? <LoadingState label="Carregando ocupação" /> : <><Typography component="p" sx={{ color: 'primary.main', fontSize: 'clamp(2.8rem, 5vw, 4rem)', fontWeight: 850, lineHeight: 1 }}>{occupancy.occupancy}</Typography><Typography color="text.secondary">{occupancy.occupancy === 1 ? 'cliente na academia' : 'clientes na academia'}</Typography>{occupancy.status === 'current' ? <StatusNotice severity="success">Contagem atualizada pela entrada e saída confirmadas.</StatusNotice> : <StatusNotice severity="info">Última contagem conhecida. A fonte de acesso está desatualizada.</StatusNotice>}</>}
      </Stack></CardContent></Card>
    </Box>
    <Card component="section"><CardContent><Stack spacing={2}>
      <Box><Typography color="text.secondary" variant="overline">Frequência recente</Typography><Typography component="h3" variant="h4">Entradas confirmadas por semana</Typography><Typography color="text.secondary" variant="body2">Total de entradas confirmadas no controle de acesso. Não representa clientes únicos nem tempo de permanência.</Typography></Box>
      {attendanceError ? <IndicatorError message={attendanceError} onRetry={loadAttendance} /> : attendance === null ? <LoadingState label="Carregando frequência" /> : <Box component="ul" sx={{ display: 'grid', gap: 1, gridTemplateColumns: { xs: 'repeat(2, minmax(0, 1fr))', sm: 'repeat(4, minmax(0, 1fr))', lg: 'repeat(8, minmax(0, 1fr))' }, listStyle: 'none', m: 0, p: 0 }}>
        {attendance.weeks.map((week) => <Box component="li" key={week.week_start} sx={{ minWidth: 0, p: 1.25, borderRadius: 1.5, bgcolor: 'rgba(245,247,244,0.025)' }}>
          <Box aria-hidden="true" sx={{ height: 88, display: 'flex', alignItems: 'flex-end', mb: 1.5, borderBottom: '1px solid', borderColor: 'divider' }}>
            <Box sx={{ width: '100%', height: `${100 * week.confirmed_entries / Math.max(1, ...attendance.weeks.map((item) => item.confirmed_entries))}%`, bgcolor: 'primary.main', borderRadius: '6px 6px 0 0', maxWidth: 40, mx: 'auto' }} />
          </Box>
          <Typography color="text.secondary" variant="caption">Semana de {formatWeek(week.week_start)}</Typography><Typography sx={{ color: 'primary.main', fontSize: '1.8rem', fontWeight: 800, lineHeight: 1.2 }}>{week.confirmed_entries}</Typography><Typography color="text.secondary" variant="caption">entradas</Typography></Box>)}
      </Box>}
    </Stack></CardContent></Card>
  </Stack>
}

function IndicatorError({ message, onRetry }: { message: string; onRetry: () => void }) {
  return <Stack spacing={1.25} sx={{ alignItems: 'flex-start' }}><StatusNotice severity="error">{message}</StatusNotice><Button onClick={onRetry} size="small" variant="outlined">Tentar novamente</Button></Stack>
}
