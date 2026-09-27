import { Avatar, Button, Card, CardContent, IconButton, Stack, Typography } from '@mui/material'
import { RouterButtonLink } from './components/router-button-link'
import { PostMedia } from './post-media'
import { fetchProgressImage, type ProgressUpdate } from './progress'
const date = (value: string) => new Intl.DateTimeFormat('pt-BR', { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(value))
export function PostCard({ post, accessToken, onOpen, onLike, onEdit, fetchImage = fetchProgressImage, readOnly = false }: { post: Omit<ProgressUpdate, 'is_own' | 'author_profile_id' | 'updated_at' | 'edited_at' | 'image_count'> & Partial<Pick<ProgressUpdate, 'author_profile_id' | 'edited_at'>>; accessToken: string; onOpen?: () => void; onLike?: () => void; onEdit?: () => void; fetchImage?: typeof fetchProgressImage; readOnly?: boolean }) {
  return <Card component="article" role={onOpen ? 'link' : undefined} tabIndex={onOpen ? 0 : undefined} aria-label={onOpen ? `Abrir publicação de ${post.author_name}` : undefined} sx={{ cursor: onOpen ? 'pointer' : undefined }} onClick={(event) => { if (!(event.target as HTMLElement).closest('button,a')) onOpen?.() }} onKeyDown={(event) => { if (event.target === event.currentTarget && ['Enter', ' '].includes(event.key) && onOpen) { event.preventDefault(); onOpen() } }}><CardContent><Stack spacing={1}>
    <Stack direction="row" spacing={1} sx={{ alignItems: 'center', flexWrap: 'wrap', overflowWrap: 'anywhere' }}><Avatar>{post.author_name.slice(0, 1)}</Avatar>
      {!readOnly && post.author_profile_id ? <RouterButtonLink to={`/perfis/${post.author_profile_id}`} variant="text">{post.author_name}</RouterButtonLink> : <Typography sx={{ fontWeight: 700 }}>{post.author_name}</Typography>}
      <Typography color="text.secondary" variant="body2">{date(post.created_at)}</Typography>
    </Stack>
    {post.content && <Typography sx={{ whiteSpace: 'pre-wrap', overflowWrap: 'anywhere' }}>{post.content}</Typography>}
    <PostMedia accessToken={accessToken} post={post} fetchImage={fetchImage}/>
    {post.edited_at && <Typography color="text.secondary" variant="caption">editado</Typography>}
    <Stack direction="row" sx={{ alignItems: 'center', flexWrap: 'wrap', gap: 1 }}>
      {!readOnly && onLike ? <Button aria-label={post.liked_by_viewer ? 'Descurtir publicação' : 'Curtir publicação'} onClick={onLike}>{post.liked_by_viewer ? '♥' : '♡'} {post.like_count}</Button> : <Typography>{post.like_count} curtidas</Typography>}
      {onOpen ? <Button aria-label="Abrir comentários" onClick={onOpen}>💬 {post.comment_count} comentários</Button> : <Typography>{post.comment_count} comentários</Typography>}
      {!readOnly && onEdit && <IconButton aria-label="Editar publicação" onClick={onEdit}><span aria-hidden="true">✎</span></IconButton>}
    </Stack>
  </Stack></CardContent></Card>
}
