import { Box, Button, Card, CardContent, Stack, Typography } from '@mui/material'
import { useEffect, useState } from 'react'

import { InstructorShell } from './instructor-shell'
import { EmptyState, LoadingState, PageHeader, StatusNotice } from './components/ui'
import { getInstructorFeed, type ProgressUpdate } from './instructor-social'

const date = (value: string) => new Intl.DateTimeFormat('pt-BR', { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(value))
export function InstructorFeedPage({ accessToken, onSignOut, onOpenPost }: { accessToken: string; onSignOut: () => void; onOpenPost: (id: string) => void }) {
  const [items, setItems] = useState<ProgressUpdate[] | null>(null); const [cursor, setCursor] = useState<string | null>(null); const [end, setEnd] = useState(false); const [error, setError] = useState<string | null>(null)
  const load = (next?: string) => { void getInstructorFeed(accessToken, next).then((page) => { setItems((old) => next ? [...(old ?? []), ...page.items] : page.items); setCursor(page.next_cursor); setEnd(page.end_reached) }).catch(() => setError('Não foi possível carregar as publicações.')) }
  useEffect(() => { load() }, [accessToken])
  return <InstructorShell onSignOut={onSignOut}><Stack spacing={3}><PageHeader eyebrow="Feed" title="Publicações" description="Acompanhe publicações de perfis públicos. Este espaço é somente para leitura." />{error && <StatusNotice severity="error">{error}</StatusNotice>}{!items ? <LoadingState label="Carregando publicações" /> : items.length === 0 ? <EmptyState title="Nenhuma publicação disponível" description="As publicações de perfis públicos aparecerão aqui." /> : <Stack spacing={2}>{items.map((item) => <Card component="article" key={item.id}><CardContent><Stack spacing={1}><Typography sx={{ fontWeight: 700 }}>{item.author_name}</Typography><Typography color="text.secondary" variant="body2">{date(item.created_at)}</Typography>{item.content && <Typography sx={{ overflowWrap: 'anywhere', whiteSpace: 'pre-wrap' }}>{item.content}</Typography>}<Stack direction="row" spacing={1}><Typography color="text.secondary">♡ {item.like_count}</Typography><Button onClick={() => onOpenPost(item.id)} variant="text">💬 {item.comment_count} comentários</Button></Stack></Stack></CardContent></Card>)}{!end && <Box><Button onClick={() => cursor && load(cursor)} variant="outlined">Carregar mais publicações</Button></Box>}{end && <Typography color="text.secondary">Você chegou ao fim das publicações.</Typography>}</Stack>}</Stack></InstructorShell>
}
