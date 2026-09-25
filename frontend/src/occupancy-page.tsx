import { Button, Card, CardContent, Stack, Typography } from '@mui/material'
import { useEffect, useState } from 'react'

import { ClientShell } from './components/application-shell'
import { LoadingState, PageHeader, StatusNotice } from './components/ui'
import { getOccupancy, type Occupancy } from './occupancy'

export function OccupancyPage({ onSignOut }: { onSignOut: () => void }) {
  const [value, setValue] = useState<Occupancy | null>(null)
  const [error, setError] = useState<string | null>(null)
  const load = () => {
    setError(null); setValue(null)
    void getOccupancy().then(setValue).catch((reason: unknown) => setError(reason instanceof Error ? reason.message : 'Não foi possível consultar a ocupação agora.'))
  }
  useEffect(load, [])
  return <ClientShell onSignOut={onSignOut} showClientNavigation><Stack spacing={3} sx={{ maxWidth: 680, minWidth: 0 }}>
    <PageHeader eyebrow="Ocupação" title="Clientes presentes" description="Esta contagem é anônima e indica somente clientes presentes na academia." />
    {error && <Stack spacing={1.5} sx={{ alignItems: 'flex-start' }}><StatusNotice severity="error">{error}</StatusNotice><Button onClick={load} variant="outlined">Tentar novamente</Button></Stack>}
    {!error && !value && <LoadingState label="Consultando ocupação" />}
    {value && <Card component="section"><CardContent sx={{ p: { xs: 3, sm: 4 } }}><Stack spacing={2} sx={{ alignItems: 'flex-start' }}>
      <Typography color="text.secondary" variant="overline">Agora na academia</Typography>
      <Typography component="p" sx={{ color: 'primary.main', fontSize: { xs: '5rem', sm: '6rem' }, fontWeight: 850, lineHeight: 0.9 }}>{value.occupancy}</Typography>
      <Typography component="h2" variant="h3">{value.occupancy === 1 ? 'cliente presente' : 'clientes presentes'}</Typography>
      {value.status === 'current' ? <StatusNotice severity="success">Contagem atualizada pela entrada e saída confirmadas.</StatusNotice> : <StatusNotice severity="info">Última contagem conhecida. A conexão com o controle de acesso está desatualizada.</StatusNotice>}
    </Stack></CardContent></Card>}
  </Stack></ClientShell>
}
