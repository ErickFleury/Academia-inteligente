import { Alert, Button, Card, CardContent, Chip, FormControlLabel, Stack, Switch, Typography } from '@mui/material'
import { useEffect, useState } from 'react'

import { ClientShell } from './components/application-shell'
import { LoadingState, PageHeader, StatusNotice } from './components/ui'
import { getOwnProfilePresence, type ProfilePresence, updateOwnProfilePresence } from './profile-presence'

export function ProfilePresencePage({ accessToken, onSignOut }: { accessToken: string; onSignOut: () => void }) {
  const [presence, setPresence] = useState<ProfilePresence | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)

  const load = () => {
    setError(null)
    void getOwnProfilePresence(accessToken)
      .then(setPresence)
      .catch((reason: unknown) => setError(reason instanceof Error ? reason.message : 'Não foi possível carregar o perfil.'))
  }

  useEffect(load, [accessToken])

  const changePreference = (enabled: boolean) => {
    setSaving(true)
    setError(null)
    void updateOwnProfilePresence(accessToken, enabled)
      .then(setPresence)
      .catch((reason: unknown) => setError(reason instanceof Error ? reason.message : 'Não foi possível atualizar a preferência.'))
      .finally(() => setSaving(false))
  }

  return <ClientShell onSignOut={onSignOut} showClientNavigation><Stack spacing={3} sx={{ maxWidth: 680, minWidth: 0 }}>
    <PageHeader eyebrow="Meu perfil" title="Presença na academia" description="Você decide se seu perfil pode mostrar que está na academia. A ocupação geral continua anônima." />
    {error && <Stack spacing={1.5} sx={{ alignItems: 'flex-start' }}><StatusNotice severity="error">{error}</StatusNotice><Button onClick={load} variant="outlined">Tentar novamente</Button></Stack>}
    {!presence && !error && <LoadingState label="Carregando preferências do perfil" />}
    {presence && <Card component="section"><CardContent sx={{ p: { xs: 3, sm: 4 } }}><Stack spacing={2.5}>
      <FormControlLabel
        control={<Switch checked={presence.sharing_enabled} disabled={saving} onChange={(event) => changePreference(event.target.checked)} />}
        label="Mostrar no meu perfil quando eu estiver na academia"
      />
      <Typography color="text.secondary" variant="body2">Esta opção começa desativada. Desativá-la remove a indicação do perfil imediatamente e não altera a contagem anônima da academia.</Typography>
      {presence.sharing_enabled && presence.currently_present && <Chip color="success" label="Na academia" sx={{ alignSelf: 'flex-start', fontWeight: 700 }} />}
      {presence.sharing_enabled && !presence.currently_present && <Alert severity="info" variant="outlined">A indicação aparecerá quando houver uma entrada confirmada e a fonte de acesso estiver atualizada.</Alert>}
    </Stack></CardContent></Card>}
  </Stack></ClientShell>
}
