import { Button, Card, CardContent, Chip, Stack, TextField, Typography } from '@mui/material'
import { useEffect, useRef, useState } from 'react'
import { AdminShell } from './components/application-shell'
import { RouterButtonLink } from './components/router-button-link'
import { EmptyState, LoadingState, PageHeader, StatusNotice } from './components/ui'
import { getModerationUpdates, moderateProgressUpdate, type ProgressUpdate } from './progress'

type ModerationAction = 'hide' | 'restore' | 'delete'
type Feedback = { id: string | null; severity: 'success' | 'error'; message: string }
const successMessages: Record<ModerationAction, string> = {
  hide: 'Publicação ocultada com sucesso.',
  restore: 'Publicação restaurada com sucesso.',
  delete: 'Publicação excluída com sucesso.',
}

export function ProgressModerationPage({ accessToken, onSignOut }: { accessToken: string; onSignOut: () => void }) {
  const [updates, setUpdates] = useState<ProgressUpdate[] | null>(null)
  const [reason, setReason] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [feedback, setFeedback] = useState<Feedback | null>(null)
  const [pending, setPending] = useState<{ id: string; action: ModerationAction } | null>(null)
  const inFlight = useRef(false)
  useEffect(() => {
    let active = true
    setUpdates(null); setError(null); setFeedback(null)
    void getModerationUpdates(accessToken).then((items) => { if (active) setUpdates(items) }).catch(() => {
      if (active) { setError('Não foi possível carregar as publicações.'); setUpdates([]) }
    })
    return () => { active = false }
  }, [accessToken])

  async function act(id: string, action: ModerationAction) {
    if (inFlight.current) return
    setFeedback(null)
    if (action !== 'delete' && !reason.trim()) {
      setFeedback({ id, severity: 'error', message: 'Informe o motivo para ocultar ou restaurar.' })
      return
    }
    if (action === 'delete' && !window.confirm('Excluir esta publicação permanentemente?')) return
    inFlight.current = true
    setPending({ id, action })
    try {
      const item = await moderateProgressUpdate(accessToken, id, action, reason.trim() || undefined)
      setUpdates((all) => action === 'delete' ? all?.filter((value) => value.id !== id) ?? [] : all?.map((value) => value.id === id ? item : value) ?? [])
      setFeedback({ id: action === 'delete' ? null : id, severity: 'success', message: successMessages[action] })
    } catch {
      setFeedback({ id, severity: 'error', message: 'Não foi possível aplicar a moderação. Tente novamente.' })
    } finally {
      inFlight.current = false
      setPending(null)
    }
  }

  const header = <PageHeader action={<RouterButtonLink to="/admin" variant="outlined">Voltar ao painel</RouterButtonLink>} eyebrow="Moderação" title="Publicações compartilhadas" description="Oculte, restaure ou exclua publicações compartilhadas." />
  if (!updates) return <AdminShell onSignOut={onSignOut}><Stack spacing={3}>{header}<LoadingState label="Carregando publicações" /></Stack></AdminShell>
  return <AdminShell onSignOut={onSignOut}><Stack spacing={3}>
    {header}
    {error && <StatusNotice severity="error">{error}</StatusNotice>}
    {feedback?.id === null && <StatusNotice severity={feedback.severity}>{feedback.message}</StatusNotice>}
    <TextField label="Motivo da moderação (opcional para excluir)" value={reason} disabled={!!pending} onChange={(e) => setReason(e.target.value)} />
    {updates.length === 0 && !error ? <EmptyState title="Nenhuma publicação" description="Não há publicações compartilhadas para moderar." /> : updates.map((item) => <Card component="article" aria-label={`Publicação de ${item.author_name}`} key={item.id}><CardContent><Stack spacing={1.5}>
      <Stack direction="row" sx={{ alignItems: 'center', justifyContent: 'space-between', gap: 1, flexWrap: 'wrap' }}>
        <Typography component="h2" variant="h4">{item.author_name}</Typography>
        <Chip label={item.moderation_status === 'hidden' ? 'Oculta' : 'Visível'} color={item.moderation_status === 'hidden' ? 'warning' : 'success'} variant="outlined" />
      </Stack>
      <Typography sx={{ whiteSpace: 'pre-wrap', overflowWrap: 'anywhere' }}>{item.content}</Typography>
      {item.moderation_reason && <Typography variant="body2" color="text.secondary" sx={{ overflowWrap: 'anywhere' }}>Último motivo de moderação: {item.moderation_reason}</Typography>}
      {feedback?.id === item.id && <StatusNotice severity={feedback.severity}>{feedback.message}</StatusNotice>}
      <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1}>
        <Button disabled={!!pending || item.moderation_status === 'hidden'} onClick={() => void act(item.id, 'hide')} variant="outlined">{pending?.id === item.id && pending.action === 'hide' ? 'Ocultando...' : 'Ocultar'}</Button>
        <Button disabled={!!pending || item.moderation_status === 'visible'} onClick={() => void act(item.id, 'restore')} variant="outlined">{pending?.id === item.id && pending.action === 'restore' ? 'Restaurando...' : 'Restaurar'}</Button>
        <Button disabled={!!pending} color="error" onClick={() => void act(item.id, 'delete')} variant="outlined">{pending?.id === item.id && pending.action === 'delete' ? 'Excluindo...' : 'Excluir publicação'}</Button>
      </Stack>
    </Stack></CardContent></Card>)}
  </Stack></AdminShell>
}
