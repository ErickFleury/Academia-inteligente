import { Button, Card, CardContent, Stack, Typography } from '@mui/material'
import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'

import { InstructorShell } from './instructor-shell'
import { LoadingState, PageHeader, StatusNotice } from './components/ui'
import { PostMedia } from './post-media'
import { PostCard } from './post-card'
import { fetchInstructorPostImage, fetchInstructorCommentImage, getInstructorPostDetail } from './instructor-social'
import type { PostDetail } from './social'

export function InstructorPostDetailPage({ accessToken, onSignOut, postId }: { accessToken: string; onSignOut: () => void; postId: string }) {
  const navigate = useNavigate(); const [detail, setDetail] = useState<PostDetail | null>(null); const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  async function load() { setLoading(true); setError(null); try { setDetail(await getInstructorPostDetail(accessToken, postId)) } catch { setError('Não foi possível carregar a publicação.') } finally { setLoading(false) } }
  useEffect(() => { void load() }, [accessToken, postId])
  return <InstructorShell onSignOut={onSignOut}><Stack spacing={3} sx={{ maxWidth: 760, mx: 'auto' }}><PageHeader action={<Button onClick={() => navigate('/instrutor/feed')}>Voltar</Button>} eyebrow="Publicação" title="Detalhes da publicação" />{error && <StatusNotice severity="error">{error}</StatusNotice>}{loading && <LoadingState label="Carregando publicação" />}{error && <Button onClick={() => void load()}>Tentar novamente</Button>}{detail && <><PostCard post={detail.post} accessToken={accessToken} readOnly fetchImage={fetchInstructorPostImage}/><Typography component="h2" variant="h3">Comentários</Typography><Stack spacing={1}>{detail.comments.map((comment) => <Card key={comment.id} component="article" sx={{ bgcolor: 'rgba(245,247,244,0.025)' }}><CardContent><Typography sx={{ fontWeight: 700 }}>{comment.author.nickname || comment.author.name}</Typography>{comment.content && <Typography sx={{ overflowWrap: 'anywhere' }}>{comment.content}</Typography>}{comment.image && <PostMedia accessToken={accessToken} post={{ id: postId, author_name: comment.author.name, images: [comment.image] }} fetchImage={fetchInstructorCommentImage} description={`Imagem do comentário de ${comment.author.nickname || comment.author.name}`}/>}</CardContent></Card>)}</Stack></>}</Stack></InstructorShell>
}
