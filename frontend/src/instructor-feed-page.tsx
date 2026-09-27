import { Button, Stack, Typography } from '@mui/material'
import { useEffect, useState } from 'react'
import { InstructorShell } from './instructor-shell'
import { EmptyState, LoadingState, PageHeader, StatusNotice } from './components/ui'
import { PostCard } from './post-card'
import { fetchInstructorPostImage, getInstructorFeed, type ProgressUpdate } from './instructor-social'
export function InstructorFeedPage({ accessToken, onSignOut, onOpenPost }: { accessToken: string; onSignOut: () => void; onOpenPost: (id: string) => void }) {
  const [items, setItems] = useState<ProgressUpdate[]>([])
  const [cursor, setCursor] = useState<string | null>(null)
  const [end, setEnd] = useState(false)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  async function load(next?: string) {
    setLoading(true); setError(null)
    try { const page = await getInstructorFeed(accessToken, next); setItems((old) => next ? [...old, ...page.items.filter((item) => !old.some((previous) => previous.id === item.id))] : page.items); setCursor(page.next_cursor); setEnd(page.end_reached) }
    catch { setError('Não foi possível carregar as publicações.') }
    finally { setLoading(false) }
  }
  useEffect(() => { void load() }, [accessToken])
  return <InstructorShell onSignOut={onSignOut}><Stack spacing={3} sx={{ maxWidth: 760, mx: 'auto' }}>
    <PageHeader eyebrow="Feed" title="Publicações" description="Acompanhe publicações de perfis públicos. Este espaço é somente para leitura."/>
    {error && <StatusNotice severity="error">{error}</StatusNotice>}
    <Button disabled={loading} onClick={() => void load()}>Recarregar publicações</Button>
    {loading && <LoadingState label="Carregando publicações"/>}
    {!loading && !error && !items.length && <EmptyState title="Nenhuma publicação disponível" description="As publicações de perfis públicos aparecerão aqui."/>}
    {items.map((item) => <PostCard key={item.id} post={item} accessToken={accessToken} readOnly fetchImage={fetchInstructorPostImage} onOpen={() => onOpenPost(item.id)}/>)}
    {!end && cursor && <Button disabled={loading} onClick={() => void load(cursor)}>Carregar mais publicações</Button>}
    {end && <Typography>Você chegou ao fim das publicações.</Typography>}
  </Stack></InstructorShell>
}
