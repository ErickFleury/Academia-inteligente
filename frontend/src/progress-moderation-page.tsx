import { Button, Card, CardContent, Stack, TextField, Typography } from '@mui/material'
import { useEffect, useState } from 'react'
import { AdminShell } from './components/application-shell'
import { RouterButtonLink } from './components/router-button-link'
import { EmptyState, LoadingState, PageHeader, StatusNotice } from './components/ui'
import { getModerationUpdates, moderateProgressUpdate, type ProgressUpdate } from './progress'

export function ProgressModerationPage({ accessToken, onSignOut }: { accessToken: string; onSignOut: () => void }) {
  const [updates, setUpdates] = useState<ProgressUpdate[] | null>(null); const [reason, setReason] = useState(''); const [error, setError] = useState<string | null>(null)
  useEffect(() => { void getModerationUpdates(accessToken).then(setUpdates).catch(() => { setError('Não foi possível carregar as publicações.'); setUpdates([]) }) }, [accessToken])
  async function act(id: string, action: 'hide' | 'restore' | 'delete') { if (action === 'delete' && !window.confirm('Excluir esta publicação permanentemente?')) return; try { const item = await moderateProgressUpdate(accessToken, id, action, reason || undefined); setUpdates((all) => action === 'delete' ? all?.filter((value) => value.id !== id) ?? [] : all?.map((value) => value.id === id ? item : value) ?? []) } catch { setError('Não foi possível aplicar a moderação.') } }
  const header = <PageHeader action={<RouterButtonLink to="/admin" variant="outlined">Voltar ao painel</RouterButtonLink>} eyebrow="Moderação" title="Publicações compartilhadas" description="Oculte, restaure ou exclua publicações compartilhadas." />
  if (!updates) return <AdminShell onSignOut={onSignOut}><Stack spacing={3}>{header}<LoadingState label="Carregando publicações" /></Stack></AdminShell>
  return <AdminShell onSignOut={onSignOut}><Stack spacing={3}>{header}{error && <StatusNotice severity="error">{error}</StatusNotice>}<TextField label="Motivo da moderação (opcional para excluir)" value={reason} onChange={(e) => setReason(e.target.value)} />{updates.length === 0 ? <EmptyState title="Nenhuma publicação" description="Não há publicações compartilhadas para moderar." /> : updates.map((item) => <Card key={item.id}><CardContent><Stack spacing={1}><Typography variant="h4">{item.author_name}</Typography><Typography>{item.content}</Typography><Stack direction={{ xs: 'column', sm: 'row' }} spacing={1}><Button onClick={() => void act(item.id, 'hide')} variant="outlined">Ocultar</Button><Button onClick={() => void act(item.id, 'restore')} variant="outlined">Restaurar</Button><Button color="error" onClick={() => void act(item.id, 'delete')} variant="outlined">Excluir publicação</Button></Stack></Stack></CardContent></Card>)}</Stack></AdminShell>
}
