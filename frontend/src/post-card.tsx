import { Avatar, Box, Button, Card, CardContent, IconButton, Stack, Typography } from '@mui/material'
import { RouterButtonLink } from './components/router-button-link'
import { WorkspaceIcon } from './components/workspace-presentation'
import { PostMedia } from './post-media'
import { fetchProgressImage, type ProgressUpdate } from './progress'
const date = (value: string) => new Intl.DateTimeFormat('pt-BR', { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(value))
export function PostCard({ post, accessToken, onOpen, onLike, onEdit, fetchImage = fetchProgressImage, readOnly = false }: { post: Omit<ProgressUpdate, 'is_own' | 'author_profile_id' | 'updated_at' | 'edited_at' | 'image_count'> & Partial<Pick<ProgressUpdate, 'author_profile_id' | 'edited_at'>>; accessToken: string; onOpen?: () => void; onLike?: () => void; onEdit?: () => void; fetchImage?: typeof fetchProgressImage; readOnly?: boolean }) {
  return <Card component="article" role={onOpen ? 'link' : undefined} tabIndex={onOpen ? 0 : undefined} aria-label={onOpen ? `Abrir publicação de ${post.author_name}` : undefined}
    sx={{ cursor: onOpen ? 'pointer' : undefined, transition: 'border-color 150ms ease', '&:hover': { borderColor: onOpen ? 'text.secondary' : 'divider' } }}
    onClick={(event) => { if (!(event.target as HTMLElement).closest('button,a')) onOpen?.() }}
    onKeyDown={(event) => { if (event.target === event.currentTarget && ['Enter', ' '].includes(event.key) && onOpen) { event.preventDefault(); onOpen() } }}>
    <CardContent><Stack spacing={2}>
      <Stack direction="row" spacing={1.5} sx={{ alignItems: 'center', overflowWrap: 'anywhere' }}>
        <Avatar sx={{ bgcolor: 'rgba(255,133,100,0.12)', color: 'primary.main', height: 44, width: 44 }}>{post.author_name.slice(0, 1)}</Avatar>
        <Box sx={{ minWidth: 0, flex: 1 }}>
          {!readOnly && post.author_profile_id
            ? <RouterButtonLink to={`/perfis/${post.author_profile_id}`} variant="text" sx={{ p: 0, justifyContent: 'flex-start', textAlign: 'left' }}>{post.author_name}</RouterButtonLink>
            : <Typography sx={{ fontWeight: 750 }}>{post.author_name}</Typography>}
          <Typography color="text.secondary" variant="caption" component="p">{date(post.created_at)}</Typography>
        </Box>
        {!readOnly && onEdit && <IconButton aria-label="Editar publicação" onClick={onEdit}><WorkspaceIcon name="edit" /></IconButton>}
      </Stack>
      {post.content && <Typography sx={{ whiteSpace: 'pre-wrap', overflowWrap: 'anywhere' }}>{post.content}</Typography>}
      <PostMedia accessToken={accessToken} post={post} fetchImage={fetchImage}/>
      {post.edited_at && <Typography color="text.secondary" variant="caption">editado</Typography>}
      <Stack direction="row" sx={{ alignItems: 'center', flexWrap: 'wrap', gap: 1, borderTop: '1px solid', borderColor: 'divider', pt: 1 }}>
        {!readOnly && onLike
          ? <Button aria-label={post.liked_by_viewer ? 'Descurtir publicação' : 'Curtir publicação'} onClick={onLike} aria-pressed={post.liked_by_viewer} sx={{ '& path': { fill: post.liked_by_viewer ? 'currentColor' : 'none' } }} startIcon={<WorkspaceIcon name="heart" />} color={post.liked_by_viewer ? 'primary' : 'inherit'}>{post.like_count}</Button>
          : <Typography variant="body2" color="text.secondary">{post.like_count} curtidas</Typography>}
        {onOpen ? <Button aria-label="Abrir comentários" onClick={onOpen} startIcon={<WorkspaceIcon name="comment" />} color="inherit">{post.comment_count} comentários</Button> : <Typography variant="body2" color="text.secondary">{post.comment_count} comentários</Typography>}
      </Stack>
    </Stack></CardContent>
  </Card>
}
