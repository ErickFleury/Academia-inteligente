import { Button, Card, CardContent, Stack, Typography } from '@mui/material'
import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'

import { InstructorShell } from './instructor-shell'
import { LoadingState, PageHeader, StatusNotice } from './components/ui'
import { getInstructorPostDetail } from './instructor-social'
import type { PostDetail } from './social'

export function InstructorPostDetailPage({ accessToken, onSignOut, postId }: { accessToken: string; onSignOut: () => void; postId: string }) {
  const navigate = useNavigate(); const [detail, setDetail] = useState<PostDetail | null>(null); const [error, setError] = useState<string | null>(null)
  useEffect(() => { void getInstructorPostDetail(accessToken, postId).then(setDetail).catch(() => setError('Não foi possível carregar a publicação.')) }, [accessToken, postId])
  return <InstructorShell onSignOut={onSignOut}><Stack spacing={3}><PageHeader action={<Button onClick={() => navigate('/instrutor/feed')}>Voltar</Button>} eyebrow="Publicação" title="Detalhes da publicação" />{error && <StatusNotice severity="error">{error}</StatusNotice>}{!detail ? <LoadingState label="Carregando publicação" /> : <><Card><CardContent><Stack spacing={1}><Typography sx={{ fontWeight: 700 }}>{detail.author.nickname || detail.author.name}</Typography>{detail.post.content && <Typography sx={{ whiteSpace: 'pre-wrap' }}>{detail.post.content}</Typography>}<Typography color="text.secondary">♡ {detail.like_count} · 💬 {detail.comments.length}</Typography></Stack></CardContent></Card><Typography component="h2" variant="h3">Comentários</Typography><Stack spacing={1}>{detail.comments.map((comment) => <Card key={comment.id}><CardContent><Typography sx={{ fontWeight: 700 }}>{comment.author.nickname || comment.author.name}</Typography>{comment.content && <Typography>{comment.content}</Typography>}</CardContent></Card>)}</Stack></>}</Stack></InstructorShell>
}
